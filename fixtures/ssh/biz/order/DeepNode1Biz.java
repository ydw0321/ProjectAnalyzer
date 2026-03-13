package com.legacy.ssh.biz.order;

import com.legacy.ssh.service.impl.payment.DeepNode2PaymentService;

public class DeepNode1Biz {

    private DeepNode2PaymentService deepNode2PaymentService = new DeepNode2PaymentService();

    public String step1(String token) {
        return deepNode2PaymentService.step2(token + "-1");
    }
}