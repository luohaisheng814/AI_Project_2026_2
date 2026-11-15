package com.busan.tour;

/**
 * 端侧小模型推理包装：llama.cpp JNI + Qwen2.5-0.5B-Instruct GGUF。
 * 只在后台线程调用，避免阻塞 WebView。
 */
public final class LocalLlm {
    static {
        System.loadLibrary("busanllm");
    }

    private static boolean inited = false;
    private static boolean loaded = false;
    private static String loadedPath = "";

    private static native int native_init(String nativeLibDir);
    private static native int native_load(String modelPath);
    private static native int native_prepare();
    private static native int native_processSystemPrompt(String prompt);
    private static native int native_processUserPrompt(String prompt, int nPredict);
    private static native String native_generateNextToken();
    private static native void native_unload();
    private static native void native_shutdown();

    private LocalLlm() {}

    public static synchronized boolean init(String nativeLibDir) {
        if (inited) return true;
        int code = native_init(nativeLibDir == null ? "" : nativeLibDir);
        inited = code == 0;
        return inited;
    }

    public static synchronized boolean ensureLoaded(String nativeLibDir, String modelPath) {
        if (!init(nativeLibDir)) return false;
        if (loaded && modelPath.equals(loadedPath)) return true;
        if (loaded) {
            native_unload();
            loaded = false;
            loadedPath = "";
        }
        if (native_load(modelPath) != 0) return false;
        if (native_prepare() != 0) {
            native_unload();
            return false;
        }
        loaded = true;
        loadedPath = modelPath;
        return true;
    }

    /** 同步生成；调用方必须在后台线程执行。 */
    public static synchronized String generate(String system, String user, int maxTokens) {
        if (!loaded) return "";
        if (native_processSystemPrompt(system == null ? "" : system) != 0) return "";
        if (native_processUserPrompt(user == null ? "" : user, maxTokens) != 0) return "";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < maxTokens; i++) {
            String piece = native_generateNextToken();
            if (piece == null) break;
            sb.append(piece);
        }
        return sb.toString().trim();
    }

    public static synchronized void release() {
        if (loaded) {
            native_unload();
            loaded = false;
            loadedPath = "";
        }
        if (inited) {
            native_shutdown();
            inited = false;
        }
    }
}
