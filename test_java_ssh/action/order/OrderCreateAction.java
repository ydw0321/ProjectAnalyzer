package com.legacy.ssh.action.order;

import com.legacy.ssh.form.order.OrderForm;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.service.OrderService;
import com.legacy.ssh.service.impl.order.OrderServiceImpl;
import com.legacy.ssh.util.common.DateUtil;

public class OrderCreateAction {

    private OrderService orderService = new OrderServiceImpl();

    public String execute(OrderForm form) {
        if (!validateInput(form)) {
            return "FAIL:invalid input";
        }

        Order order = orderService.submitOrder(
            form.getUserId(),
            form.getProductCode(),
            form.getQuantity(),
            form.getPaymentChannel()
        );

        String stamp = DateUtil.formatNow();
        return "OK:" + order.getOrderId() + ":" + stamp;
    }

    private boolean validateInput(OrderForm form) {
        if (form == null) {
            return false;
        }
        if (form.getUserId() == null || form.getUserId().trim().isEmpty()) {
            return false;
        }
        if (form.getProductCode() == null || form.getProductCode().trim().isEmpty()) {
            return false;
        }
        return form.getQuantity() > 0;
    }
}
