#pragma once

#ifdef _WIN32
#define GL_EFFECTS_API __declspec(dllexport)
#else
#define GL_EFFECTS_API extern "C" __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

#define GL_EFFECTS_VERSION "1.0.0"

typedef enum {
    GL_EFFECTS_SUCCESS = 0,
    GL_EFFECTS_ERROR_INVALID_PARAM = -1,
    GL_EFFECTS_ERROR_INIT_FAILED = -2,
    GL_EFFECTS_ERROR_RENDER_FAILED = -3,
    GL_EFFECTS_ERROR_MEMORY = -4,
    GL_EFFECTS_ERROR_UNSUPPORTED = -5
} GLEffectsError;

typedef struct {
    float r;
    float g;
    float b;
    float a;
} GLColor;

typedef struct {
    int x;
    int y;
    int width;
    int height;
} GLRect;

typedef struct {
    float blur_radius;
    float opacity;
    GLColor tint_color;
    float border_width;
    GLColor border_color;
    bool enable_border_sharp;
} GlassEffectParams;

typedef struct {
    GLColor glow_color;
    float glow_intensity;
    float glow_radius;
    GLColor shadow_color;
    float shadow_offset_x;
    float shadow_offset_y;
    float shadow_blur;
} GlowEffectParams;

typedef struct {
    int target_width;
    int target_height;
    int target_x;
    int target_y;
    float duration;
    int easing_type;
} WindowAnimationParams;

GL_EFFECTS_API const char* gl_effects_get_version();

GL_EFFECTS_API GLEffectsError gl_effects_init(uint32_t width, uint32_t height, void* native_window);

GL_EFFECTS_API void gl_effects_shutdown();

GL_EFFECTS_API GLEffectsError gl_effects_set_transparency(float alpha);

GL_EFFECTS_API float gl_effects_get_transparency();

GL_EFFECTS_API GLEffectsError gl_effects_enable_glass_effect(bool enable);

GL_EFFECTS_API bool gl_effects_is_glass_enabled();

GL_EFFECTS_API GLEffectsError gl_effects_set_glass_params(const GlassEffectParams* params);

GL_EFFECTS_API GLEffectsError gl_effects_get_glass_params(GlassEffectParams* params);

GL_EFFECTS_API GLEffectsError gl_effects_enable_glow_effect(bool enable);

GL_EFFECTS_API bool gl_effects_is_glow_enabled();

GL_EFFECTS_API GLEffectsError gl_effects_set_glow_params(const GlowEffectParams* params);

GL_EFFECTS_API GLEffectsError gl_effects_get_glow_params(GlowEffectParams* params);

GL_EFFECTS_API GLEffectsError gl_effects_start_window_animation(const WindowAnimationParams* params);

GL_EFFECTS_API bool gl_effects_is_animating();

GL_EFFECTS_API GLEffectsError gl_effects_render();

GL_EFFECTS_API void gl_effects_set_log_callback(void (*callback)(const char* message));

GL_EFFECTS_API const char* gl_effects_get_error_message(GLEffectsError error);

#ifdef __cplusplus
}
#endif