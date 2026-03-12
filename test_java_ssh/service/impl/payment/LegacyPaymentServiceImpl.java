package com.legacy.ssh.service.impl.payment;

import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.service.PaymentService;
import com.legacy.ssh.util.common.DateUtil;
import com.legacy.ssh.util.common.LegacyCodeUtil;

public class LegacyPaymentServiceImpl implements PaymentService {

    @Override
    public String pay(Order order) {
        if (order == null) {
            return "FAIL:ORDER_NULL";
        }
        if ("COD".equals(order.getPaymentChannel())) {
            return "CASH-" + order.getOrderId();
        }

        String seq = "PAY-" + DateUtil.nowMillis();
        LegacyCodeUtil.debug("pay seq=" + seq);
        return seq;
    }

    @Override
    public boolean reverse(Order order) {
        if (order == null) {
            return false;
        }
        return order.getOrderId() != null;
    }

    @Override
    public String getChannelCode() {
        return "LEGACY_GATEWAY";
    }
}
