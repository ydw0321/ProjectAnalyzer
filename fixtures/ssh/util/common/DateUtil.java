package com.legacy.ssh.util.common;

import java.text.SimpleDateFormat;
import java.util.Date;

public class DateUtil {

    public static String formatNow() {
        return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date());
    }

    public static long nowMillis() {
        return System.currentTimeMillis();
    }

    public static boolean expired(long ts, int seconds) {
        long diff = nowMillis() - ts;
        return diff > (seconds * 1000L);
    }
}
