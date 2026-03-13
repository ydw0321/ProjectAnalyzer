package com.legacy.ssh.action.order;

import com.legacy.ssh.form.order.OrderForm;
import com.legacy.ssh.service.OrderService;
import com.legacy.ssh.service.impl.order.OrderServiceProxy;

public class OrderManageAction {

    private OrderService orderService = new OrderServiceProxy();

    public String approve(OrderForm form) {
        if (form == null || form.getOrderId() == null) {
            return "FAIL:no order";
        }
        orderService.queryOrder(form.getOrderId());
        return "OK:approved";
    }

    public String reject(OrderForm form) {
        if (form == null) {
            return "FAIL:no form";
        }
        orderService.cancelOrder(form.getOrderId(), "manual reject");
        return "OK:rejected";
    }
}
