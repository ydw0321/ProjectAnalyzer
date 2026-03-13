package com.legacy.ssh.service;

import com.legacy.ssh.model.order.Order;

public interface OrderService {

    Order submitOrder(String userId, String productCode, int quantity, String paymentChannel);

    void cancelOrder(String orderId, String reason);

    Order queryOrder(String orderId);

    void reconcile(String batchNo);
}
