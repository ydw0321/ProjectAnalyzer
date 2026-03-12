package com.legacy.ssh.action.order;

import com.legacy.ssh.form.order.OrderForm;
import com.legacy.ssh.service.impl.order.DeepChainCoordinator;
import com.legacy.ssh.service.impl.order.LegacyTicketMonsterService;

public class LegacyStressAction {

    private DeepChainCoordinator deepChainCoordinator = new DeepChainCoordinator();
    private LegacyTicketMonsterService legacyTicketMonsterService = new LegacyTicketMonsterService();

    public String execute(OrderForm form) {
        if (form == null) {
            return "FAIL:NO_FORM";
        }
        String orderId = form.getOrderId() == null ? "ORD-STRESS" : form.getOrderId();
        String chain = deepChainCoordinator.start(orderId);
        String monster = legacyTicketMonsterService.execute(orderId);
        return chain + "|" + monster;
    }
}