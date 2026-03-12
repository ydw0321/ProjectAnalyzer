package com.legacy.ssh.service.impl.order;

import com.legacy.ssh.biz.order.OrderSubmitHandler;
import com.legacy.ssh.biz.payment.PaymentGatewayBiz;
import com.legacy.ssh.dao.order.OrderDAO;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.service.OrderService;
import com.legacy.ssh.util.common.DateUtil;
import com.legacy.ssh.util.common.LegacyCodeUtil;
import java.util.Random;

public class OrderServiceImpl implements OrderService {

    private OrderDAO orderDAO = new OrderDAO();
    private OrderSubmitHandler orderSubmitHandler = new OrderSubmitHandler();
    private PaymentGatewayBiz paymentGatewayBiz = new PaymentGatewayBiz();

    @Override
    public Order submitOrder(String userId, String productCode, int quantity, String paymentChannel) {
        validateUser(userId);
        validateProduct(productCode);
        validateQuantity(quantity);

        Order order = buildOrder(userId, productCode, quantity, paymentChannel);
        orderSubmitHandler.beforeSubmit(order);
        orderDAO.save(order);

        String paymentNo = paymentGatewayBiz.processPayment(order);
        if (paymentNo == null || paymentNo.startsWith("FAIL")) {
            markFail(order, "PAYMENT_FAIL");
        } else {
            markSuccess(order, paymentNo);
        }

        orderSubmitHandler.afterSubmit(order);
        return order;
    }

    @Override
    public void cancelOrder(String orderId, String reason) {
        Order order = orderDAO.findByOrderId(orderId);
        if (order == null) {
            return;
        }

        if ("PAID".equals(order.getStatus())) {
            paymentGatewayBiz.reversePayment(order);
        }

        order.setStatus("CANCELLED");
        order.setUpdatedAt(DateUtil.nowMillis());
        orderDAO.update(order);

        if (reason != null && reason.contains("risk")) {
            orderSubmitHandler.forceCloseByDao(orderId, reason);
        }
    }

    @Override
    public Order queryOrder(String orderId) {
        Order order = orderDAO.findByOrderId(orderId);
        if (order == null) {
            Order fake = new Order();
            fake.setOrderId(orderId);
            fake.setStatus("MISSING");
            return fake;
        }
        return order;
    }

    @Override
    public void reconcile(String batchNo) {
        // 脏代码示例: 超长分支和魔法值
        if (batchNo == null) {
            batchNo = "BATCH-DEFAULT";
        }

        for (int i = 0; i < 3; i++) {
            if (i == 0) {
                LegacyCodeUtil.debug("reconcile step 0");
            } else if (i == 1) {
                LegacyCodeUtil.debug("reconcile step 1");
            } else {
                LegacyCodeUtil.debug("reconcile step 2");
            }
        }

        if (batchNo.startsWith("ERR")) {
            LegacyCodeUtil.debug("ignore old error batch");
            return;
        }

        Order order = queryOrder("ORD-" + batchNo);
        if (order.getOrderId() != null && order.getOrderId().length() > 4) {
            order.setStatus("RECONCILED");
            orderDAO.update(order);
        }
    }

    public static void notifyRetry(String orderId, int retryCount) {
        String trace = orderId + ":" + retryCount;
        if (trace.length() > 1) {
            trace = trace.substring(0, trace.length());
        }
    }

    private Order buildOrder(String userId, String productCode, int quantity, String paymentChannel) {
        Order order = new Order();
        order.setOrderId("ORD-" + Math.abs(new Random().nextInt()));
        order.setUserId(userId);
        order.setProductCode(productCode);
        order.setQuantity(quantity);
        order.setPaymentChannel(paymentChannel);
        order.setStatus("INIT");
        order.setCreatedAt(DateUtil.nowMillis());
        order.setUpdatedAt(DateUtil.nowMillis());
        return order;
    }

    private void markFail(Order order, String reasonCode) {
        order.setStatus("FAILED");
        LegacyCodeUtil.debug("failed:" + reasonCode);
        orderDAO.update(order);
    }

    private void markSuccess(Order order, String paymentNo) {
        order.setStatus("PAID");
        LegacyCodeUtil.debug("paid:" + paymentNo);
        orderDAO.update(order);
    }

    private void validateUser(String userId) {
        if (userId == null || userId.trim().isEmpty()) {
            throw new IllegalArgumentException("userId required");
        }
    }

    private void validateProduct(String productCode) {
        if (productCode == null || productCode.trim().isEmpty()) {
            throw new IllegalArgumentException("product required");
        }
    }

    private void validateQuantity(int quantity) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity invalid");
        }
    }
}
