package com.legacy.ssh.service.impl.order;

import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.service.OrderService;
import com.legacy.ssh.util.common.LegacyCodeUtil;

public class OrderServiceProxy implements OrderService {

    private OrderService target = new OrderServiceImpl();

    @Override
    public Order submitOrder(String userId, String productCode, int quantity, String paymentChannel) {
        LegacyCodeUtil.debug("proxy submit");
        return target.submitOrder(userId, productCode, quantity, paymentChannel);
    }

    @Override
    public void cancelOrder(String orderId, String reason) {
        LegacyCodeUtil.debug("proxy cancel");
        target.cancelOrder(orderId, reason);
    }

    @Override
    public Order queryOrder(String orderId) {
        return target.queryOrder(orderId);
    }

    @Override
    public void reconcile(String batchNo) {
        target.reconcile(batchNo);
    }
}
