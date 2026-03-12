package com.legacy.ssh.biz.order;

import com.legacy.ssh.dao.order.OrderDAO;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.common.LegacyCodeUtil;

public class OrderCancelHandler {

    private OrderDAO orderDAO = new OrderDAO();

    public void handle(String orderId) {
        Order order = orderDAO.findByOrderId(orderId);
        if (order == null) {
            return;
        }

        if ("PAID".equals(order.getStatus())) {
            LegacyCodeUtil.debug("need refund later");
        }

        order.setStatus("CANCELLED");
        orderDAO.update(order);
    }
}
