package com.legacy.ssh.service.impl.payment;

import com.legacy.ssh.model.order.Order;
import com.legacy.ssh.service.PaymentService;
import com.legacy.ssh.util.common.DateUtil;

public class AlipayPaymentServiceImpl implements PaymentService {

    @Override
    public String pay(Order order) {
        if (order == null) {
            return "FAIL";
        }
        return "ALI-" + DateUtil.nowMillis();
    }

    @Override
    public boolean reverse(Order order) {
        return order != null;
    }

    @Override
    public String getChannelCode() {
        return "ALIPAY";
    }
}
