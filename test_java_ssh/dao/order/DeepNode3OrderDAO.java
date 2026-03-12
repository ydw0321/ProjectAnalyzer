package com.legacy.ssh.dao.order;

import com.legacy.ssh.util.common.DeepNode4Util;

public class DeepNode3OrderDAO {

    private DeepNode4Util deepNode4Util = new DeepNode4Util();

    public String step3(String token) {
        return deepNode4Util.step4(token + "-3");
    }
}