package com.legacy.ssh.action.order;

import com.legacy.ssh.form.order.OrderForm;
import com.legacy.ssh.service.impl.order.DeepChainCoordinator;
import com.legacy.ssh.service.impl.order.LegacyMegaWorkflowService;

public class LegacyDeepChainAction {

    private LegacyMegaWorkflowService legacyMegaWorkflowService = new LegacyMegaWorkflowService();
    private DeepChainCoordinator deepChainCoordinator = new DeepChainCoordinator();

    public String execute(OrderForm form) {
        if (form == null || form.getOrderId() == null) {
            return "FAIL:NO_ORDER";
        }
        String a = legacyMegaWorkflowService.execute(form.getOrderId());
        String b = deepChainCoordinator.start(form.getOrderId());
        return a + "|" + b;
    }

    public String process(OrderForm form) {
        return execute(form);
    }
}
