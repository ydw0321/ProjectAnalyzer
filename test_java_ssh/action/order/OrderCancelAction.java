package com.legacy.ssh.action.order;

import com.legacy.ssh.biz.order.OrderSubmitHandler;
import com.legacy.ssh.form.order.OrderForm;
import com.legacy.ssh.service.OrderService;
import com.legacy.ssh.service.impl.order.OrderServiceImpl;

public class OrderCancelAction {

    private OrderService orderService = new OrderServiceImpl();
    private OrderSubmitHandler submitHandler = new OrderSubmitHandler();

    public String execute(OrderForm form) {
        if (form == null || form.getOrderId() == null) {
            return "FAIL:orderId required";
        }

        // 越级路径: Action 直接调 Biz, 模拟遗留逻辑绕过 Service
        if ("Y".equals(form.getOperator())) {
            submitHandler.forceCloseByDao(form.getOrderId(), "operator force close");
            return "OK:forceClosed";
        }

        orderService.cancelOrder(form.getOrderId(), "user action");
        return "OK:cancelled";
    }
}
