package com.legacy.ssh.util.cache;

import java.util.HashMap;
import java.util.Map;

public class LocalCache {

    private static Map<String, String> STORE = new HashMap<String, String>();

    public static void put(String key, String value) {
        STORE.put(key, value);
    }

    public static String get(String key) {
        return STORE.get(key);
    }

    public static void clear() {
        STORE.clear();
    }
}
