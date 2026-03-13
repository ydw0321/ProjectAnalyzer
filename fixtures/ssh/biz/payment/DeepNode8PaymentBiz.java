package com.legacy.ssh.biz.payment;

import com.legacy.ssh.dao.base.DeepNode9BaseDAO;

public class DeepNode8PaymentBiz {

    private DeepNode9BaseDAO deepNode9BaseDAO = new DeepNode9BaseDAO();

    public String step8(String token) {
        return deepNode9BaseDAO.step9(token + "-8");
    }
}