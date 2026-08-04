#include "gl_effects.h"
#include <vector>
#include <string>
#include <memory>
#include <cmath>

#ifdef _WIN32
#include <windows.h>
#include <gl/GL.h>
#pragma comment(lib, "opengl32.lib")
#else
#include <GL/gl.h>
#include <GL/glu.h>
#include <dlfcn.h>
#endif

static void (*g_log_callback)(const char*) = nullptr;

#define LOG_INFO(msg) do { if (g_log_callback) g_log_callback(msg); } while(0)
#define LOG_ERROR(msg) do { if (g_log_callback) g_log_callback(msg); } while(0)

struct GLEffectsState {
    uint32_t width = 0;
    uint32_t height = 0;
    void* native_window = nullptr;
    
    float transparency = 1.0f;
    
    bool glass_enabled = false;
    GlassEffectParams glass_params = {
        .blur_radius = 20.0f,
        .opacity = 0.8f,
        .tint_color = {0.1f, 0.1f, 0.15f, 0.6f},
        .border_width = 1.0f,
        .border_color = {0.9f, 0.9f, 0.95f, 0.8f},
        .enable_border_sharp = true
    };
    
    bool glow_enabled = false;
    GlowEffectParams glow_params = {
        .glow_color = {0.2f, 0.5f, 1.0f, 0.6f},
        .glow_intensity = 0.8f,
        .glow_radius = 15.0f,
        .shadow_color = {0.0f, 0.0f, 0.0f, 0.3f},
        .shadow_offset_x = 2.0f,
        .shadow_offset_y = 4.0f,
        .shadow_blur = 10.0f
    };
    
    bool is_animating = false;
    WindowAnimationParams anim_params;
    float anim_progress = 0.0f;
    float anim_start_time = 0.0f;
    
    int current_frame = 0;
    double last_time = 0.0;
    double frame_time_accum = 0.0;
    int fps_frame_count = 0;
    float current_fps = 0.0f;
};

static std::unique_ptr<GLEffectsState> g_state;

static double get_time() {
#ifdef _WIN32
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart / (double)freq.QuadPart;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
#endif
}

static float ease_out_cubic(float t) {
    return 1.0f - powf(1.0f - t, 3.0f);
}

static float ease_in_out_cubic(float t) {
    return t < 0.5f ? 4.0f * t * t * t : 1.0f - powf(-2.0f * t + 2.0f, 3.0f) / 2.0f;
}

static float apply_easing(float t, int easing_type) {
    switch (easing_type) {
        case 1: return ease_out_cubic(t);
        case 2: return ease_in_out_cubic(t);
        default: return t;
    }
}

static void update_animation() {
    if (!g_state->is_animating) return;
    
    double now = get_time();
    float elapsed = (float)(now - g_state->anim_start_time);
    float duration = g_state->anim_params.duration;
    
    if (elapsed >= duration) {
        g_state->anim_progress = 1.0f;
        g_state->is_animating = false;
    } else {
        g_state->anim_progress = apply_easing(elapsed / duration, g_state->anim_params.easing_type);
    }
}

static void render_blur(float radius) {
    int iterations = (int)ceil(radius / 4.0f);
    float step = radius / (float)iterations;
    
    for (int i = 0; i < iterations; ++i) {
        float blur = step * (float)(i + 1);
        
        glPushMatrix();
        glTranslatef(blur, 0, 0);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glColor4f(0, 0, 0, 0.05f);
        glRecti(0, 0, g_state->width, g_state->height);
        glPopMatrix();
        
        glPushMatrix();
        glTranslatef(-blur, 0, 0);
        glColor4f(0, 0, 0, 0.05f);
        glRecti(0, 0, g_state->width, g_state->height);
        glPopMatrix();
        
        glPushMatrix();
        glTranslatef(0, blur, 0);
        glColor4f(0, 0, 0, 0.05f);
        glRecti(0, 0, g_state->width, g_state->height);
        glPopMatrix();
        
        glPushMatrix();
        glTranslatef(0, -blur, 0);
        glColor4f(0, 0, 0, 0.05f);
        glRecti(0, 0, g_state->width, g_state->height);
        glPopMatrix();
    }
}

static void render_glass_effect() {
    if (!g_state->glass_enabled) return;
    
    const auto& params = g_state->glass_params;
    
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    
    render_blur(params.blur_radius);
    
    glColor4f(params.tint_color.r, params.tint_color.g, params.tint_color.b, 
              params.tint_color.a * params.opacity * g_state->transparency);
    glRecti(0, 0, g_state->width, g_state->height);
    
    if (params.enable_border_sharp && params.border_width > 0) {
        glLineWidth(params.border_width);
        glColor4f(params.border_color.r, params.border_color.g, 
                  params.border_color.b, params.border_color.a);
        glBegin(GL_LINE_LOOP);
        glVertex2i(0, 0);
        glVertex2i(g_state->width, 0);
        glVertex2i(g_state->width, g_state->height);
        glVertex2i(0, g_state->height);
        glEnd();
    }
    
    glDisable(GL_BLEND);
}

static void render_glow_effect() {
    if (!g_state->glow_enabled) return;
    
    const auto& params = g_state->glow_params;
    
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    
    float glow_intensity = params.glow_intensity * g_state->transparency;
    
    for (float r = params.glow_radius; r > 0; r -= 2.0f) {
        float alpha = glow_intensity * (1.0f - r / params.glow_radius);
        glColor4f(params.glow_color.r, params.glow_color.g, 
                  params.glow_color.b, alpha * 0.3f);
        
        glBegin(GL_QUADS);
        glVertex2i(-(int)r, -(int)r);
        glVertex2i(g_state->width + (int)r, -(int)r);
        glVertex2i(g_state->width + (int)r, g_state->height + (int)r);
        glVertex2i(-(int)r, g_state->height + (int)r);
        glEnd();
    }
    
    glColor4f(params.glow_color.r, params.glow_color.g, 
              params.glow_color.b, glow_intensity * 0.5f);
    glRecti(0, 0, g_state->width, g_state->height);
    
    glColor4f(params.shadow_color.r, params.shadow_color.g, 
              params.shadow_color.b, params.shadow_color.a);
    glPushMatrix();
    glTranslatef(params.shadow_offset_x, params.shadow_offset_y, 0);
    glRecti(0, 0, g_state->width, g_state->height);
    glPopMatrix();
    
    glDisable(GL_BLEND);
}

GL_EFFECTS_API const char* gl_effects_get_version() {
    return GL_EFFECTS_VERSION;
}

GL_EFFECTS_API GLEffectsError gl_effects_init(uint32_t width, uint32_t height, void* native_window) {
    try {
        g_state = std::make_unique<GLEffectsState>();
        g_state->width = width;
        g_state->height = height;
        g_state->native_window = native_window;
        g_state->last_time = get_time();
        
        LOG_INFO("GL Effects initialized successfully");
        return GL_EFFECTS_SUCCESS;
    } catch (...) {
        LOG_ERROR("GL Effects initialization failed");
        return GL_EFFECTS_ERROR_INIT_FAILED;
    }
}

GL_EFFECTS_API void gl_effects_shutdown() {
    g_state.reset();
    LOG_INFO("GL Effects shutdown");
}

GL_EFFECTS_API GLEffectsError gl_effects_set_transparency(float alpha) {
    if (!g_state) return GL_EFFECTS_ERROR_INIT_FAILED;
    if (alpha < 0.0f || alpha > 1.0f) return GL_EFFECTS_ERROR_INVALID_PARAM;
    
    g_state->transparency = alpha;
    return GL_EFFECTS_SUCCESS;
}

GL_EFFECTS_API float gl_effects_get_transparency() {
    return g_state ? g_state->transparency : 1.0f;
}

GL_EFFECTS_API GLEffectsError gl_effects_enable_glass_effect(bool enable) {
    if (!g_state) return GL_EFFECTS_ERROR_INIT_FAILED;
    g_state->glass_enabled = enable;
    return GL_EFFECTS_SUCCESS;
}

GL_EFFECTS_API bool gl_effects_is_glass_enabled() {
    return g_state ? g_state->glass_enabled : false;
}

GL_EFFECTS_API GLEffectsError gl_effects_set_glass_params(const GlassEffectParams* params) {
    if (!g_state || !params) return GL_EFFECTS_ERROR_INVALID_PARAM;
    g_state->glass_params = *params;
    return GL_EFFECTS_SUCCESS;
}

GL_EFFECTS_API GLEffectsError gl_effects_get_glass_params(GlassEffectParams* params) {
    if (!g_state || !params) return GL_EFFECTS_ERROR_INVALID_PARAM;
    *params = g_state->glass_params;
    return GL_EFFECTS_SUCCESS;
}

GL_EFFECTS_API GLEffectsError gl_effects_enable_glow_effect(bool enable) {
    if (!g_state) return GL_EFFECTS_ERROR_INIT_FAILED;
    g_state->glow_enabled = enable;
    return GL_EFFECTS_SUCCESS;
}

GL_EFFECTS_API bool gl_effects_is_glow_enabled() {
    return g_state ? g_state->glow_enabled : false;
}

GL_EFFECTS_API GLEffectsError gl_effects_set_glow_params(const GlowEffectParams* params) {
    if (!g_state || !params) return GL_EFFECTS_ERROR_INVALID_PARAM;
    g_state->glow_params = *params;
    return GL_EFFECTS_SUCCESS;
}

GL_EFFECTS_API GLEffectsError gl_effects_get_glow_params(GlowEffectParams* params) {
    if (!g_state || !params) return GL_EFFECTS_ERROR_INVALID_PARAM;
    *params = g_state->glow_params;
    return GL_EFFECTS_SUCCESS;
}

GL_EFFECTS_API GLEffectsError gl_effects_start_window_animation(const WindowAnimationParams* params) {
    if (!g_state || !params) return GL_EFFECTS_ERROR_INVALID_PARAM;
    
    g_state->anim_params = *params;
    g_state->anim_progress = 0.0f;
    g_state->anim_start_time = get_time();
    g_state->is_animating = true;
    
    return GL_EFFECTS_SUCCESS;
}

GL_EFFECTS_API bool gl_effects_is_animating() {
    return g_state ? g_state->is_animating : false;
}

GL_EFFECTS_API GLEffectsError gl_effects_render() {
    if (!g_state) return GL_EFFECTS_ERROR_INIT_FAILED;
    
    update_animation();
    
    double now = get_time();
    double delta = now - g_state->last_time;
    g_state->last_time = now;
    
    g_state->frame_time_accum += delta;
    g_state->fps_frame_count++;
    if (g_state->frame_time_accum >= 1.0) {
        g_state->current_fps = (float)g_state->fps_frame_count / (float)g_state->frame_time_accum;
        g_state->fps_frame_count = 0;
        g_state->frame_time_accum = 0.0;
    }
    
    glEnable(GL_SCISSOR_TEST);
    glScissor(0, 0, g_state->width, g_state->height);
    
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, g_state->width, g_state->height, 0, -1, 1);
    
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    
    render_glow_effect();
    render_glass_effect();
    
    glDisable(GL_SCISSOR_TEST);
    g_state->current_frame++;
    
    return GL_EFFECTS_SUCCESS;
}

GL_EFFECTS_API void gl_effects_set_log_callback(void (*callback)(const char* message)) {
    g_log_callback = callback;
}

GL_EFFECTS_API const char* gl_effects_get_error_message(GLEffectsError error) {
    switch (error) {
        case GL_EFFECTS_SUCCESS: return "Success";
        case GL_EFFECTS_ERROR_INVALID_PARAM: return "Invalid parameter";
        case GL_EFFECTS_ERROR_INIT_FAILED: return "Initialization failed";
        case GL_EFFECTS_ERROR_RENDER_FAILED: return "Render failed";
        case GL_EFFECTS_ERROR_MEMORY: return "Memory allocation failed";
        case GL_EFFECTS_ERROR_UNSUPPORTED: return "Unsupported operation";
        default: return "Unknown error";
    }
}