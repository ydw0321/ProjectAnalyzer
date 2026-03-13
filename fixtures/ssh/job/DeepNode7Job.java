package com.legacy.ssh.job;

import com.legacy.ssh.biz.payment.DeepNode8PaymentBiz;

public class DeepNode7Job {

    private DeepNode8PaymentBiz deepNode8PaymentBiz = new DeepNode8PaymentBiz();

    public String step7(String token) {
        return deepNode8PaymentBiz.step8(token + "-7");
    }
}