package com.legacy.ssh.action.order;

import com.legacy.ssh.service.OrderService;
import com.legacy.ssh.service.impl.order.OrderServiceAsync;

public class OrderQueryAction {

    private OrderService orderService = new OrderServiceAsync();

    public String execute(String orderId) {
        if (orderId == null || orderId.trim().isEmpty()) {
            return "FAIL:missing id";
        }
        return orderService.queryOrder(orderId).getStatus();
    }
}
