package com.legacy.ssh.util.cache;

import java.util.HashMap;
import java.util.Map;

public class CacheUtil {

    private static Map<String, String> CACHE = new HashMap<String, String>();

    static {
        initCache();
    }

    private static void initCache() {
        CACHE.put("channel.default", "ALIPAY");
        CACHE.put("risk.switch", "ON");
    }

    public static String get(String key) {
        return CACHE.get(key);
    }

    public static void put(String key, String value) {
        CACHE.put(key, value);
    }
}
