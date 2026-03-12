package com.legacy.ssh.legacy.integration;

import com.legacy.ssh.util.common.LegacyCodeUtil;

public class LegacyRpcClient {

    public String post(String service, String payload) {
        LegacyCodeUtil.debug("rpc post:" + service);
        if (payload == null) {
            return "FAIL";
        }
        return "OK";
    }
}
