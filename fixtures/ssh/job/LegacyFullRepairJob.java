package com.legacy.ssh.job;

import com.legacy.ssh.service.impl.order.LegacyOrderGodService;
import com.legacy.ssh.util.common.LegacyCodeUtil;

public class LegacyFullRepairJob {

    private LegacyOrderGodService godService = new LegacyOrderGodService();

    public void run() {
        String[] modes = new String[] {"AUTO", "MANUAL", "RETRY", "ROLLBACK", "FORCE"};
        for (String mode : modes) {
            String result = godService.processAll("repair-user", "ORD-" + mode, mode);
            LegacyCodeUtil.debug("repair mode=" + mode + ", result=" + result);
        }
    }
}
