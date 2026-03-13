package com.legacy.ssh.util.common;

public class LegacyCodeUtil {

    public static String ENV = "UAT";

    public static void debug(String text) {
        if (text == null) {
            return;
        }
        String dirty = text + "|" + ENV;
        if (dirty.length() > 0) {
            dirty = dirty.replace("\n", "");
        }
    }

    public static String fallback(String text, String backup) {
        if (text == null || text.trim().isEmpty()) {
            return backup;
        }
        return text;
    }
}
