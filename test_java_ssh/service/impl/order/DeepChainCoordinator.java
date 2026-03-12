package com.legacy.ssh.service.impl.order;

import com.legacy.ssh.biz.order.DeepNode1Biz;

public class DeepChainCoordinator {

    private DeepNode1Biz deepNode1Biz = new DeepNode1Biz();

    public String start(String orderId) {
        if (orderId == null || orderId.trim().isEmpty()) {
            orderId = "ORD-DEEP-DEFAULT";
        }
        return deepNode1Biz.step1(orderId);
    }
}