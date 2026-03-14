package com.example.util;

import java.text.SimpleDateFormat;
import java.util.Date;

public class DateUtil {
    
    private static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
    
    public static String formatDateTime(Date date) {
        if (date == null) return null;
        return DATE_FORMAT.format(date);
    }
    
    public static Date addDays(Date date, int days) {
        if (date == null) return null;
        long time = date.getTime() + (long) days * 24 * 60 * 60 * 1000;
        return new Date(time);
    }
    
    public static boolean isExpired(Date date) {
        if (date == null) return false;
        return date.before(new Date());
    }
}
