package com.legacy.ssh.util.common;

public class LegacyExecuteHelper {

    public static String execute(String id) {
        return "EXEC:" + id;
    }

    public static String process(String id) {
        return "PROC:" + id;
    }

    public static String save(String id) {
        return "SAVE:" + id;
    }
}
