package com.legacy.ssh.service.impl.order;

import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.service.OrderService;

public class OrderServiceAsync implements OrderService {

    private OrderService delegate = new OrderServiceImpl();

    @Override
    public Order submitOrder(String userId, String productCode, int quantity, String paymentChannel) {
        return delegate.submitOrder(userId, productCode, quantity, paymentChannel);
    }

    @Override
    public void cancelOrder(String orderId, String reason) {
        delegate.cancelOrder(orderId, reason);
    }

    @Override
    public Order queryOrder(String orderId) {
        return delegate.queryOrder(orderId);
    }

    @Override
    public void reconcile(String batchNo) {
        // 模拟老系统异步包装层
        String asyncBatch = "ASYNC-" + batchNo;
        delegate.reconcile(asyncBatch);
    }
}
