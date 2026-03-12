package com.legacy.ssh.util.common;

public class SqlBuilderUtil {

    public static String buildSelectOrder(String id) {
        return "select * from t_order where order_id='" + id + "'";
    }

    public static String buildUpdateStatus(String id, String status) {
        return "update t_order set status='" + status + "' where order_id='" + id + "'";
    }
}
