package com.legacy.ssh.job;

import com.legacy.ssh.dao.order.OrderStatisticsDAO;
import com.legacy.ssh.util.cache.LocalCache;

public class LegacyCleanupJob {

    private OrderStatisticsDAO orderStatisticsDAO = new OrderStatisticsDAO();

    public void run() {
        int size = orderStatisticsDAO.countOrderByDate("2020-01-01");
        if (size > 0) {
            LocalCache.clear();
        }
    }
}
