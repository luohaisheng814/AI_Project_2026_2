#pragma once

#include <android/log.h>
#include <cstdarg>
#include "ggml.h"

#define BUSAN_LOG_TAG "BusanLLM"

static void aichat_android_log_callback(enum ggml_log_level level, const char *text, void * /*user_data*/) {
    int prio = ANDROID_LOG_DEBUG;
    if (level == GGML_LOG_LEVEL_ERROR) prio = ANDROID_LOG_ERROR;
    else if (level == GGML_LOG_LEVEL_WARN) prio = ANDROID_LOG_WARN;
    else if (level == GGML_LOG_LEVEL_INFO) prio = ANDROID_LOG_INFO;
    __android_log_print(prio, BUSAN_LOG_TAG, "%s", text ? text : "");
}

#define LOGi(...) __android_log_print(ANDROID_LOG_INFO,  BUSAN_LOG_TAG, __VA_ARGS__)
#define LOGw(...) __android_log_print(ANDROID_LOG_WARN,  BUSAN_LOG_TAG, __VA_ARGS__)
#define LOGe(...) __android_log_print(ANDROID_LOG_ERROR, BUSAN_LOG_TAG, __VA_ARGS__)
#define LOGd(...) __android_log_print(ANDROID_LOG_DEBUG, BUSAN_LOG_TAG, __VA_ARGS__)
#define LOGv(...) __android_log_print(ANDROID_LOG_VERBOSE, BUSAN_LOG_TAG, __VA_ARGS__)
