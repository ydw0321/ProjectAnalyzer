package com.legacy.ssh.dao.order;

import com.legacy.ssh.util.common.LegacyCodeUtil;

public class OrderStatisticsDAO {

    public int countOrderByDate(String dateKey) {
        if (dateKey == null) {
            return 0;
        }
        return dateKey.length();
    }

    public String summarizeUser(String userId) {
        LegacyCodeUtil.debug("summarize user " + userId);
        return "SUM:" + userId;
    }
}
