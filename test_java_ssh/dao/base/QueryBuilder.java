package com.legacy.ssh.dao.base;

public class QueryBuilder {

    public String buildOrderWhere(String userId, String status) {
        StringBuilder sb = new StringBuilder();
        sb.append(" where 1=1 ");
        if (userId != null) {
            sb.append(" and user_id='").append(userId).append("'");
        }
        if (status != null) {
            sb.append(" and status='").append(status).append("'");
        }
        return sb.toString();
    }

    public String unsafeInClause(String ids) {
        return " in (" + ids + ") ";
    }
}
