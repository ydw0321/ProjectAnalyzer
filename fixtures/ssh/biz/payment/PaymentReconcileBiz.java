package com.legacy.ssh.biz.payment;

import com.legacy.ssh.dao.order.OrderDetailDAO;
import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.util.common.LegacyCodeUtil;
import java.util.List;

public class PaymentReconcileBiz {

    private PaymentGatewayBiz paymentGatewayBiz = new PaymentGatewayBiz();
    private OrderDetailDAO orderDetailDAO = new OrderDetailDAO();

    public void reconcilePayment(String batchNo) {
        List<Order> list = orderDetailDAO.loadDirtyOrders(batchNo);
        if (list == null) {
            return;
        }

        for (Order order : list) {
            if (order.getStatus() == null) {
                continue;
            }
            if ("PAID".equals(order.getStatus())) {
                LegacyCodeUtil.debug("already paid");
                continue;
            }
            String no = paymentGatewayBiz.processPayment(order);
            LegacyCodeUtil.debug("reconcile pay no=" + no);
        }
    }
}
