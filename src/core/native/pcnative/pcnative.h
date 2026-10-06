/*
 * pcnative.h - powerful-claw 原生加速内核（纯 C ABI）
 *
 * 覆盖四组热点：
 *   1) 图像 ASCII / 像素矩阵
 *   2) 帧差分块编码规划
 *   3) 标量表达式求值
 *   4) 核心计算 / 网络封包 pack/unpack
 *
 * 约定：
 *   - 所有失败通过返回码 + pcn_last_error() 获取原因；
 *   - 库内 malloc 返回的缓冲必须由 pcn_free() 释放；
 *   - C++ 异常不跨越本 ABI。
 */
#ifndef PCNATIVE_H
#define PCNATIVE_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PCN_OK  0
#define PCN_ERR 1

/* 版本与诊断 */
const char* pcn_version(void);
const char* pcn_last_error(void);
void        pcn_free(void* ptr);

/* ================= 1. 图像热点 ================= */

/* 将已缩放为 width*height 的灰度像素映射为 ASCII 字符串。
   invert 非 0 时使用反转字符表。返回 malloc 的 NUL 结尾字符串。 */
char* pcn_ascii_gray(const unsigned char* gray,
                     int width, int height,
                     int invert, int* out_len);

/* 将 width*height 的 RGB 交错图像生成像素矩阵描述（UTF-8 文本）。 */
char* pcn_pixel_matrix_rgb(const unsigned char* rgb,
                           int width, int height,
                           int sample_size, int* out_len);

/* 稀疏路径：points 为已采样的 grid_cols*grid_rows 个 RGB 点（逐点交错），
   由调用方按原像素坐标采样；生成与 pcn_pixel_matrix_rgb 完全一致的文本。 */
char* pcn_sampled_matrix(const unsigned char* points,
                         int grid_cols, int grid_rows,
                         int orig_w, int orig_h, int* out_len);

/* ================= 2. 帧差分块编码 ================= */

typedef struct {
    int           x, y, w, h;
    unsigned int  hash;   /* 块原始 RGB 字节的 adler32 */
} pcn_block_t;

/* 依据 0/非0 的差分掩码规划需要编码的块。
   mask 为 NULL 时编码全部块；min_changed_ratio 为块内变化比例阈值（如 0.05）。
   返回写入 blocks 的块数（容量不足时截断）；out_changed 可返回变化像素总数。 */
int pcn_plan_blocks(const unsigned char* rgb,
                    const unsigned char* mask,
                    int width, int height,
                    int block_size,
                    double min_changed_ratio,
                    pcn_block_t* blocks, int cap,
                    int* out_changed);

/* 计算单个块（原始像素）adler32，用于缓存键。 */
unsigned int pcn_block_hash(const unsigned char* rgb,
                            int width, int height,
                            int x, int y, int w, int h);

/* 仅依据差分掩码扫描需编码块坐标（不访问 RGB，稀疏掩码场景零整帧拷贝）。
   返回写入 blocks 的块数；块 hash 字段不填充（置 0）。 */
int pcn_scan_mask(const unsigned char* mask,
                  int width, int height,
                  int block_size,
                  double min_changed_ratio,
                  pcn_block_t* blocks, int cap);

/* 连续字节流的 adler32（与 zlib.adler32 一致），用于块字节哈希。 */
unsigned int pcn_adler32(const unsigned char* data, int len);

/* ================= 3. 标量表达式求值 ================= */

/* 成功返回 PCN_OK 且 *out 为结果；语法/运行错误返回 PCN_ERR。
   支持 + - * / % ^ 、比较、逻辑、三目、pi/e 及常见数学函数。 */
int pcn_expr_eval(const char* expr, double* out);

/* ================= 4. 封包 / 核心计算 ================= */

/* 帧格式（小端）：
   "PCN1" | version u8 | type u8 | flags u8 | reserved u8
   sequence u32 | payload_len u32 | payload... | crc32 u32            */
unsigned char* pcn_pack(unsigned char msg_type, unsigned int sequence,
                        const unsigned char* payload,
                        unsigned int payload_len, int* out_len);

int pcn_unpack(const unsigned char* frame, int frame_len,
               unsigned char* msg_type, unsigned int* sequence,
               const unsigned char** payload, unsigned int* payload_len);

double        pcn_clamp(double x, double lo, double hi);
double        pcn_lerp(double a, double b, double t);
unsigned int  pcn_crc32(const unsigned char* data, int len);

#ifdef __cplusplus
}
#endif

#endif /* PCNATIVE_H */
