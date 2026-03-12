package com.legacy.ssh.legacy.integration;

import com.legacy.ssh.service.PaymentService;
import com.legacy.ssh.service.impl.payment.AlipayPaymentServiceImpl;
import com.legacy.ssh.service.impl.payment.WechatPaymentServiceImpl;

public class ServiceLocator {

    public static PaymentService getPaymentService(String key) {
        if ("WX".equals(key)) {
            return new WechatPaymentServiceImpl();
        }
        return new AlipayPaymentServiceImpl();
    }
}
