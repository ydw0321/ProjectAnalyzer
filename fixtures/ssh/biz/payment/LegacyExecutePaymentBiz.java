package com.legacy.ssh.biz.payment;

import com.legacy.ssh.dao.order.LegacyExecuteOrderDAO;
import com.legacy.ssh.model.order.Order;

public class LegacyExecutePaymentBiz {

    private LegacyExecuteOrderDAO legacyExecuteOrderDAO = new LegacyExecuteOrderDAO();

    public String execute(Order order) {
        return legacyExecuteOrderDAO.execute(order);
    }

    public String process(Order order) {
        return legacyExecuteOrderDAO.process(order);
    }

    public String save(Order order) {
        return legacyExecuteOrderDAO.save(order);
    }
}
