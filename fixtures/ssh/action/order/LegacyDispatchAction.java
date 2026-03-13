package com.legacy.ssh.action.order;

import com.legacy.ssh.form.order.OrderForm;
import com.legacy.ssh.service.impl.order.LegacyOrderGodService;

public class LegacyDispatchAction {

    private LegacyOrderGodService godService = new LegacyOrderGodService();

    public String execute(OrderForm form) {
        if (form == null) {
            return "FAIL:NO_FORM";
        }
        return godService.processAll(
            form.getUserId(),
            form.getOrderId(),
            form.getOperator()
        );
    }

    public String process(OrderForm form) {
        return execute(form);
    }
}
