package com.legacy.ssh.dao.order;

import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.common.LegacyExecuteHelper;

public class LegacyExecuteOrderDAO {

    public String execute(Order order) {
        return LegacyExecuteHelper.execute(order == null ? "null" : order.getOrderId());
    }

    public String process(Order order) {
        return LegacyExecuteHelper.process(order == null ? "null" : order.getOrderId());
    }

    public String save(Order order) {
        return LegacyExecuteHelper.save(order == null ? "null" : order.getOrderId());
    }
}
