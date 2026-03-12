package com.legacy.ssh.biz.order;

import com.legacy.ssh.dao.order.OrderStatisticsDAO;
import com.legacy.ssh.util.common.DateUtil;
import com.legacy.ssh.util.common.LegacyCodeUtil;

public class LegacyOrderAuditBiz {

    private OrderStatisticsDAO statisticsDAO = new OrderStatisticsDAO();

    public void auditDay(String dateKey) {
        if (dateKey == null || dateKey.trim().isEmpty()) {
            dateKey = DateUtil.formatNow().substring(0, 10);
        }
        int count = statisticsDAO.countOrderByDate(dateKey);
        LegacyCodeUtil.debug("auditDay count=" + count);
    }

    public void auditUser(String userId) {
        String result = statisticsDAO.summarizeUser(userId);
        LegacyCodeUtil.debug("auditUser:" + result);
    }
}
