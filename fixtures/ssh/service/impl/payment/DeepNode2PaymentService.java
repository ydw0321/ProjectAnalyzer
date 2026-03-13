package com.legacy.ssh.service.impl.payment;

import com.legacy.ssh.dao.order.DeepNode3OrderDAO;

public class DeepNode2PaymentService {

    private DeepNode3OrderDAO deepNode3OrderDAO = new DeepNode3OrderDAO();

    public String step2(String token) {
        return deepNode3OrderDAO.step3(token + "-2");
    }
}