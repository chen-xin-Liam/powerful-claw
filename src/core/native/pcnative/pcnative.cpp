/*
 * pcnative.cpp - powerful-claw 原生加速内核实现（C++17，无第三方依赖）
 */
#include "pcnative.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <new>
#include <string>
#include <vector>

namespace {

thread_local std::string g_last_error;

void set_error(const std::string& msg) { g_last_error = msg; }

char* dup_to_c(const std::string& s, int* out_len) {
    char* buf = static_cast<char*>(std::malloc(s.size() + 1));
    if (!buf) {
        set_error("内存分配失败");
        return nullptr;
    }
    std::memcpy(buf, s.data(), s.size());
    buf[s.size()] = '\0';
    if (out_len) *out_len = static_cast<int>(s.size());
    return buf;
}

// ---------------- adler32 / crc32 ----------------

// adler32（与 zlib 一致）：每最多 5552 字节才做一次取模，避免逐字节除法
uint32_t adler32_contig(const uint8_t* data, size_t len) {
    constexpr uint32_t MOD = 65521;
    uint32_t a = 1, b = 0;
    while (len) {
        size_t n = len < 5552 ? len : 5552;
        len -= n;
        for (size_t i = 0; i < n; ++i) {
            a += data[i];
            b += a;
        }
        a %= MOD;
        b %= MOD;
        data += n;
    }
    return (b << 16) | a;
}

// 对帧内非连续块区域求 adler32：逐行收集为连续缓冲
uint32_t adler32_region(const uint8_t* rgb, int width,
                        int x, int y, int w, int h) {
    std::vector<uint8_t> tmp;
    tmp.reserve(static_cast<size_t>(w) * h * 3);
    for (int yy = 0; yy < h; ++yy) {
        const uint8_t* row = rgb + ((y + yy) * width + x) * 3;
        tmp.insert(tmp.end(), row, row + w * 3);
    }
    return adler32_contig(tmp.data(), tmp.size());
}

// slicing-by-8 CRC32（8 张表，速度接近 zlib）
uint32_t crc_tables[8][256];

void crc_init() {
    for (uint32_t i = 0; i < 256; ++i) {
        uint32_t c = i;
        for (int k = 0; k < 8; ++k)
            c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
        crc_tables[0][i] = c;
    }
    for (int k = 1; k < 8; ++k) {
        for (uint32_t i = 0; i < 256; ++i) {
            uint32_t prev = crc_tables[k - 1][i];
            crc_tables[k][i] =
                (prev >> 8) ^ crc_tables[0][prev & 0xFF];
        }
    }
}

uint32_t crc32_bytes(const uint8_t* data, size_t len) {
    static const bool ready = (crc_init(), true);
    (void)ready;
    uint32_t c = 0xFFFFFFFFu;
    while (len >= 8) {
        c ^= uint32_t(data[0]) | (uint32_t(data[1]) << 8) |
             (uint32_t(data[2]) << 16) | (uint32_t(data[3]) << 24);
        c = crc_tables[7][c & 0xFF] ^
            crc_tables[6][(c >> 8) & 0xFF] ^
            crc_tables[5][(c >> 16) & 0xFF] ^
            crc_tables[4][(c >> 24) & 0xFF] ^
            crc_tables[3][data[4]] ^
            crc_tables[2][data[5]] ^
            crc_tables[1][data[6]] ^
            crc_tables[0][data[7]];
        data += 8;
        len -= 8;
    }
    for (size_t i = 0; i < len; ++i)
        c = crc_tables[0][(c ^ data[i]) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFFu;
}

void put_u32_le(uint8_t* p, uint32_t v) {
    p[0] = v & 0xFF;
    p[1] = (v >> 8) & 0xFF;
    p[2] = (v >> 16) & 0xFF;
    p[3] = (v >> 24) & 0xFF;
}

uint32_t get_u32_le(const uint8_t* p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) |
           (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

// ---------------- 像素矩阵 UTF-8 块字符 ----------------

const char* block_utf8(int brightness) {
    if (brightness < 64)  return "\xE2\x96\x88";  // █
    if (brightness < 128) return "\xE2\x96\x93";  // ▓
    if (brightness < 192) return "\xE2\x96\x92";  // ▒
    return "\xE2\x96\x91";                        // ░
}

// ---------------- 表达式求值 ----------------

struct ExprError : std::exception {
    std::string m;
    explicit ExprError(std::string s) : m(std::move(s)) {}
    const char* what() const noexcept override { return m.c_str(); }
};

class ExprParser {
public:
    explicit ExprParser(const char* s) : s_(s) {}

    double parse() {
        double v = parse_ternary();
        skip_ws();
        if (s_[pos_] != '\0')
            throw ExprError("意外的尾随字符 '" +
                            std::string(1, s_[pos_]) + "'");
        return v;
    }

private:
    const char* s_;
    size_t pos_ = 0;

    void skip_ws() {
        while (s_[pos_] == ' ' || s_[pos_] == '\t' ||
               s_[pos_] == '\r' || s_[pos_] == '\n')
            ++pos_;
    }

    bool match2(char a, char b) {
        if (s_[pos_] == a && s_[pos_ + 1] == b) {
            pos_ += 2;
            return true;
        }
        return false;
    }

    double parse_ternary() {
        double cond = parse_or();
        skip_ws();
        if (s_[pos_] == '?') {
            ++pos_;
            double t = parse_ternary();
            skip_ws();
            if (s_[pos_] != ':')
                throw ExprError("三目运算符缺少 ':'");
            ++pos_;
            double f = parse_ternary();
            return cond != 0.0 ? t : f;
        }
        return cond;
    }

    double parse_or() {
        double left = parse_and();
        for (;;) {
            skip_ws();
            if (match2('|', '|')) {
                double right = parse_and();
                left = (left != 0.0 || right != 0.0) ? 1.0 : 0.0;
            } else break;
        }
        return left;
    }

    double parse_and() {
        double left = parse_cmp();
        for (;;) {
            skip_ws();
            if (match2('&', '&')) {
                double right = parse_cmp();
                left = (left != 0.0 && right != 0.0) ? 1.0 : 0.0;
            } else break;
        }
        return left;
    }

    double parse_cmp() {
        double left = parse_add();
        for (;;) {
            skip_ws();
            std::string op;
            if (match2('<', '=')) op = "<=";
            else if (match2('>', '=')) op = ">=";
            else if (match2('=', '=')) op = "==";
            else if (match2('!', '=')) op = "!=";
            else if (s_[pos_] == '<') { op = "<"; ++pos_; }
            else if (s_[pos_] == '>') { op = ">"; ++pos_; }
            else break;

            double right = parse_add();
            double r = 0.0;
            if (op == "<=") r = left <= right;
            else if (op == ">=") r = left >= right;
            else if (op == "==") r = left == right;
            else if (op == "!=") r = left != right;
            else if (op == "<") r = left < right;
            else r = left > right;
            left = r;
        }
        return left;
    }

    double parse_add() {
        double left = parse_mul();
        for (;;) {
            skip_ws();
            char c = s_[pos_];
            if (c == '+' || c == '-') {
                ++pos_;
                double right = parse_mul();
                left = (c == '+') ? left + right : left - right;
            } else break;
        }
        return left;
    }

    double parse_mul() {
        double left = parse_unary();
        for (;;) {
            skip_ws();
            char c = s_[pos_];
            if (c == '*' || c == '/' || c == '%') {
                ++pos_;
                double right = parse_unary();
                if (c == '*') left *= right;
                else if (c == '/') {
                    if (right == 0.0) throw ExprError("除数为零");
                    left /= right;
                } else {
                    if (right == 0.0) throw ExprError("模数为零");
                    left = std::fmod(left, right);
                }
            } else break;
        }
        return left;
    }

    double parse_unary() {
        skip_ws();
        char c = s_[pos_];
        if (c == '+' || c == '-') {
            ++pos_;
            double v = parse_unary();
            return c == '+' ? v : -v;
        }
        return parse_pow();
    }

    double parse_pow() {
        double base = parse_primary();
        skip_ws();
        if (s_[pos_] == '^') {
            ++pos_;
            double expv = parse_unary();  // 右结合
            return std::pow(base, expv);
        }
        return base;
    }

    static bool is_ident_start(char c) {
        return std::isalpha(static_cast<unsigned char>(c)) || c == '_';
    }

    double parse_primary() {
        skip_ws();
        char c = s_[pos_];
        if (c == '(') {
            ++pos_;
            double v = parse_ternary();
            skip_ws();
            if (s_[pos_] != ')') throw ExprError("括号未闭合");
            ++pos_;
            return v;
        }
        if (std::isdigit(static_cast<unsigned char>(c)) || c == '.')
            return parse_number();
        if (is_ident_start(c))
            return parse_ident_call();
        if (c == '\0') throw ExprError("表达式意外结束");
        throw ExprError(std::string("意外的字符 '") + c + "'");
    }

    double parse_number() {
        size_t start = pos_;
        bool dot = false, expv = false;
        for (;;) {
            char ch = s_[pos_];
            if (std::isdigit(static_cast<unsigned char>(ch))) ++pos_;
            else if (ch == '.' && !dot && !expv) { dot = true; ++pos_; }
            else if ((ch == 'e' || ch == 'E') && !expv) {
                expv = true;
                ++pos_;
                if ((s_[pos_] == '+' || s_[pos_] == '-')) ++pos_;
            } else break;
        }
        std::string num = std::string(s_ + start, pos_ - start);
        if (num == "." || num.empty())
            throw ExprError("无效的数字格式");
        try {
            size_t used = 0;
            double v = std::stod(num, &used);
            if (used != num.size()) throw ExprError("无效的数字格式");
            return v;
        } catch (...) {
            throw ExprError("无法解析数字 '" + num + "'");
        }
    }

    double call_function(const std::string& name,
                         const std::vector<double>& a) {
        auto need = [&](size_t n) {
            if (a.size() != n)
                throw ExprError(name + " 参数个数错误");
        };
        if (name == "abs") { need(1); return std::fabs(a[0]); }
        if (name == "sqrt") { need(1); return std::sqrt(a[0]); }
        if (name == "cbrt") { need(1); return std::cbrt(a[0]); }
        if (name == "exp") { need(1); return std::exp(a[0]); }
        if (name == "log") { need(1); return std::log(a[0]); }
        if (name == "log2") { need(1); return std::log2(a[0]); }
        if (name == "log10") { need(1); return std::log10(a[0]); }
        if (name == "sin") { need(1); return std::sin(a[0]); }
        if (name == "cos") { need(1); return std::cos(a[0]); }
        if (name == "tan") { need(1); return std::tan(a[0]); }
        if (name == "asin") { need(1); return std::asin(a[0]); }
        if (name == "acos") { need(1); return std::acos(a[0]); }
        if (name == "atan") { need(1); return std::atan(a[0]); }
        if (name == "sinh") { need(1); return std::sinh(a[0]); }
        if (name == "cosh") { need(1); return std::cosh(a[0]); }
        if (name == "tanh") { need(1); return std::tanh(a[0]); }
        if (name == "sign") {
            need(1);
            return (a[0] > 0) - (a[0] < 0);
        }
        if (name == "pow") { need(2); return std::pow(a[0], a[1]); }
        if (name == "clamp") {
            need(3);
            return a[0] < a[1] ? a[1] : (a[0] > a[2] ? a[2] : a[0]);
        }
        if (name == "lerp") {
            need(3);
            return a[0] + (a[1] - a[0]) * a[2];
        }
        if (name == "min") {
            if (a.empty()) throw ExprError("min 至少需要 1 个参数");
            double m = a[0];
            for (double v : a) m = v < m ? v : m;
            return m;
        }
        if (name == "max") {
            if (a.empty()) throw ExprError("max 至少需要 1 个参数");
            double m = a[0];
            for (double v : a) m = v > m ? v : m;
            return m;
        }
        throw ExprError("未知函数: " + name);
    }

    double parse_ident_call() {
        size_t start = pos_;
        while (std::isalnum(static_cast<unsigned char>(s_[pos_])) ||
               s_[pos_] == '_')
            ++pos_;
        std::string name(s_ + start, pos_ - start);
        skip_ws();
        if (s_[pos_] == '(') {
            ++pos_;
            std::vector<double> args;
            skip_ws();
            if (s_[pos_] != ')') {
                args.push_back(parse_ternary());
                skip_ws();
                while (s_[pos_] == ',') {
                    ++pos_;
                    args.push_back(parse_ternary());
                    skip_ws();
                }
            }
            if (s_[pos_] != ')')
                throw ExprError("函数 '" + name + "' 的括号未闭合");
            ++pos_;
            return call_function(name, args);
        }
        if (name == "pi") return 3.14159265358979323846;
        if (name == "e") return 2.71828182845904523536;
        throw ExprError("未定义的变量: " + name);
    }
};

}  // namespace

// ==================== 导出 C ABI ====================

extern "C" {

const char* pcn_version(void) { return "pcnative 1.0.0"; }

const char* pcn_last_error(void) { return g_last_error.c_str(); }

void pcn_free(void* ptr) { std::free(ptr); }

char* pcn_ascii_gray(const unsigned char* gray,
                     int width, int height,
                     int invert, int* out_len) {
    try {
        if (!gray || width <= 0 || height <= 0) {
            set_error("ascii: 参数非法");
            return nullptr;
        }
        static const char kChars[] = "@%#*+=-:. ";
        std::string chars(kChars);
        if (invert) std::reverse(chars.begin(), chars.end());
        const size_t n = chars.size();

        std::string out;
        out.reserve(static_cast<size_t>(width) * height + height - 1);
        for (int y = 0; y < height; ++y) {
            if (y > 0) out.push_back('\n');
            for (int x = 0; x < width; ++x) {
                int px = gray[y * width + x];
                size_t idx = px * (n - 1) / 255;
                out.push_back(chars[idx]);
            }
        }
        return dup_to_c(out, out_len);
    } catch (const std::exception& e) {
        set_error(std::string("ascii 失败: ") + e.what());
        return nullptr;
    } catch (...) {
        set_error("ascii 发生未知错误");
        return nullptr;
    }
}

char* pcn_pixel_matrix_rgb(const unsigned char* rgb,
                           int width, int height,
                           int sample_size, int* out_len) {
    try {
        if (!rgb || width <= 0 || height <= 0 || sample_size <= 0) {
            set_error("pixel_matrix: 参数非法");
            return nullptr;
        }
        int step_x = std::max(1, width / sample_size);
        int step_y = std::max(1, height / sample_size);
        int cols = width / step_x;
        int rows = height / step_y;
        (void)rows;

        std::string out;
        out += "图片尺寸: " + std::to_string(width) +
               " x " + std::to_string(height);
        out += "\n采样网格: " + std::to_string(cols) +
               " x " + std::to_string(height / step_y);
        out += "\n像素矩阵:";
        out += "\n" + std::string(cols * 8, '-');

        for (int y = 0; y < height; y += step_y) {
            out += "\n|";
            for (int x = 0; x < width; x += step_x) {
                const uint8_t* p = rgb + (y * width + x) * 3;
                int br = (p[0] + p[1] + p[2]) / 3;
                out += block_utf8(br);
                out += block_utf8(br);
            }
            out += "|";
        }

        out += "\n" + std::string(cols * 8, '-');
        out += "\n\nRGB采样点:";
        for (int y = 0; y < height; y += step_y * 4) {
            out += "\n";
            bool first = true;
            for (int x = 0; x < width; x += step_x * 4) {
                const uint8_t* p = rgb + (y * width + x) * 3;
                if (!first) out += " ";
                first = false;
                out += "(" + std::to_string(p[0]) + "," +
                       std::to_string(p[1]) + "," +
                       std::to_string(p[2]) + ")";
            }
        }
        return dup_to_c(out, out_len);
    } catch (const std::exception& e) {
        set_error(std::string("pixel_matrix 失败: ") + e.what());
        return nullptr;
    } catch (...) {
        set_error("pixel_matrix 发生未知错误");
        return nullptr;
    }
}

char* pcn_sampled_matrix(const unsigned char* points,
                         int grid_cols, int grid_rows,
                         int orig_w, int orig_h, int* out_len) {
    try {
        if (!points || grid_cols <= 0 || grid_rows <= 0 ||
            orig_w <= 0 || orig_h <= 0) {
            set_error("sampled_matrix: 参数非法");
            return nullptr;
        }

        std::string out;
        out += "图片尺寸: " + std::to_string(orig_w) +
               " x " + std::to_string(orig_h);
        out += "\n采样网格: " + std::to_string(grid_cols) +
               " x " + std::to_string(grid_rows);
        out += "\n像素矩阵:";
        out += "\n" + std::string(grid_cols * 8, '-');

        int idx = 0;
        for (int r = 0; r < grid_rows; ++r) {
            out += "\n|";
            for (int c = 0; c < grid_cols; ++c) {
                const uint8_t* p = points + (idx++) * 3;
                int br = (p[0] + p[1] + p[2]) / 3;
                out += block_utf8(br);
                out += block_utf8(br);
            }
            out += "|";
        }

        out += "\n" + std::string(grid_cols * 8, '-');
        out += "\n\nRGB采样点:";
        for (int r = 0; r < grid_rows; r += 4) {
            out += "\n";
            bool first = true;
            for (int c = 0; c < grid_cols; c += 4) {
                const uint8_t* p = points + (r * grid_cols + c) * 3;
                if (!first) out += " ";
                first = false;
                out += "(" + std::to_string(p[0]) + "," +
                       std::to_string(p[1]) + "," +
                       std::to_string(p[2]) + ")";
            }
        }
        return dup_to_c(out, out_len);
    } catch (const std::exception& e) {
        set_error(std::string("sampled_matrix 失败: ") + e.what());
        return nullptr;
    } catch (...) {
        set_error("sampled_matrix 发生未知错误");
        return nullptr;
    }
}

int pcn_plan_blocks(const unsigned char* rgb,
                    const unsigned char* mask,
                    int width, int height,
                    int block_size,
                    double min_changed_ratio,
                    pcn_block_t* blocks, int cap,
                    int* out_changed) {
    try {
        if (!rgb || width <= 0 || height <= 0 ||
            block_size <= 0 || !blocks || cap <= 0) {
            set_error("plan_blocks: 参数非法");
            return PCN_ERR;
        }
        int total_changed = 0;
        int written = 0;
        for (int y = 0; y < height; y += block_size) {
            for (int x = 0; x < width; x += block_size) {
                int x2 = std::min(x + block_size, width);
                int y2 = std::min(y + block_size, height);

                bool encode = true;
                if (mask) {
                    int changed = 0;
                    int total = 0;
                    for (int yy = y; yy < y2; ++yy) {
                        const uint8_t* mp = mask + yy * width + x;
                        for (int xx = 0; xx < x2 - x; ++xx) {
                            ++total;
                            if (mp[xx] > 0) ++changed;
                        }
                    }
                    total_changed += changed;
                    double ratio = double(changed) / double(total);
                    encode = ratio >= min_changed_ratio;
                }
                if (encode && written < cap) {
                    pcn_block_t& b = blocks[written++];
                    b.x = x; b.y = y;
                    b.w = x2 - x; b.h = y2 - y;
                    b.hash = adler32_region(rgb, width, x, y, b.w, b.h);
                }
            }
        }
        if (out_changed) *out_changed = total_changed;
        return written;
    } catch (const std::exception& e) {
        set_error(std::string("plan_blocks 失败: ") + e.what());
        return PCN_ERR;
    } catch (...) {
        set_error("plan_blocks 发生未知错误");
        return PCN_ERR;
    }
}

unsigned int pcn_block_hash(const unsigned char* rgb,
                            int width, int height,
                            int x, int y, int w, int h) {
    if (!rgb || width <= 0 || height <= 0 || w <= 0 || h <= 0) return 0;
    return adler32_region(rgb, width, x, y, w, h);
}

int pcn_scan_mask(const unsigned char* mask,
                  int width, int height,
                  int block_size,
                  double min_changed_ratio,
                  pcn_block_t* blocks, int cap) {
    try {
        if (!mask || width <= 0 || height <= 0 ||
            block_size <= 0 || !blocks || cap <= 0) {
            set_error("scan_mask: 参数非法");
            return PCN_ERR;
        }
        int written = 0;
        for (int y = 0; y < height; y += block_size) {
            for (int x = 0; x < width; x += block_size) {
                int x2 = std::min(x + block_size, width);
                int y2 = std::min(y + block_size, height);
                int changed = 0, total = 0;
                for (int yy = y; yy < y2; ++yy) {
                    const uint8_t* mp = mask + yy * width + x;
                    for (int xx = 0; xx < x2 - x; ++xx) {
                        ++total;
                        if (mp[xx] > 0) ++changed;
                    }
                }
                if (double(changed) / double(total) >= min_changed_ratio &&
                    written < cap) {
                    pcn_block_t& blk = blocks[written++];
                    blk.x = x; blk.y = y;
                    blk.w = x2 - x; blk.h = y2 - y;
                    blk.hash = 0;
                }
            }
        }
        return written;
    } catch (const std::exception& e) {
        set_error(std::string("scan_mask 失败: ") + e.what());
        return PCN_ERR;
    } catch (...) {
        set_error("scan_mask 发生未知错误");
        return PCN_ERR;
    }
}

unsigned int pcn_adler32(const unsigned char* data, int len) {
    if (!data || len <= 0) return 0;
    return adler32_contig(data, static_cast<size_t>(len));
}

int pcn_expr_eval(const char* expr, double* out) {
    try {
        if (!expr || !out) {
            set_error("expr_eval: 参数非法");
            return PCN_ERR;
        }
        ExprParser parser(expr);
        *out = parser.parse();
        return PCN_OK;
    } catch (const std::exception& e) {
        set_error(std::string("表达式错误: ") + e.what());
        return PCN_ERR;
    } catch (...) {
        set_error("表达式发生未知错误");
        return PCN_ERR;
    }
}

unsigned char* pcn_pack(unsigned char msg_type, unsigned int sequence,
                        const unsigned char* payload,
                        unsigned int payload_len, int* out_len) {
    try {
        if (!out_len || (payload_len > 0 && !payload)) {
            set_error("pack: 参数非法");
            return nullptr;
        }
        const size_t total = 16 + payload_len + 4;
        auto* buf = static_cast<uint8_t*>(std::malloc(total));
        if (!buf) { set_error("pack: 内存分配失败"); return nullptr; }
        std::memcpy(buf, "PCN1", 4);
        buf[4] = 1;          // version
        buf[5] = msg_type;
        buf[6] = 0;          // flags
        buf[7] = 0;          // reserved
        put_u32_le(buf + 8, sequence);
        put_u32_le(buf + 12, payload_len);
        if (payload_len) std::memcpy(buf + 16, payload, payload_len);
        uint32_t crc = crc32_bytes(buf, 16 + payload_len);
        put_u32_le(buf + 16 + payload_len, crc);
        *out_len = static_cast<int>(total);
        return buf;
    } catch (const std::exception& e) {
        set_error(std::string("pack 失败: ") + e.what());
        return nullptr;
    }
}

int pcn_unpack(const unsigned char* frame, int frame_len,
               unsigned char* msg_type, unsigned int* sequence,
               const unsigned char** payload, unsigned int* payload_len) {
    try {
        if (!frame || frame_len < 20) {
            set_error("unpack: 帧长度不足");
            return PCN_ERR;
        }
        if (std::memcmp(frame, "PCN1", 4) != 0) {
            set_error("unpack: 魔数不匹配");
            return PCN_ERR;
        }
        if (frame[4] != 1) {
            set_error("unpack: 不支持的版本");
            return PCN_ERR;
        }
        uint32_t seq = get_u32_le(frame + 8);
        uint32_t plen = get_u32_le(frame + 12);
        if (frame_len != static_cast<int>(16 + plen + 4)) {
            set_error("unpack: 长度字段与帧不一致");
            return PCN_ERR;
        }
        uint32_t expect = get_u32_le(frame + 16 + plen);
        uint32_t actual = crc32_bytes(frame, 16 + plen);
        if (expect != actual) {
            set_error("unpack: CRC32 校验失败");
            return PCN_ERR;
        }
        if (msg_type) *msg_type = frame[5];
        if (sequence) *sequence = seq;
        if (payload) *payload = frame + 16;
        if (payload_len) *payload_len = plen;
        return PCN_OK;
    } catch (const std::exception& e) {
        set_error(std::string("unpack 失败: ") + e.what());
        return PCN_ERR;
    }
}

double pcn_clamp(double x, double lo, double hi) {
    return x < lo ? lo : (x > hi ? hi : x);
}

double pcn_lerp(double a, double b, double t) {
    return a + (b - a) * t;
}

unsigned int pcn_crc32(const unsigned char* data, int len) {
    if (!data || len <= 0) return 0;
    return crc32_bytes(data, static_cast<size_t>(len));
}

}  // extern "C"
