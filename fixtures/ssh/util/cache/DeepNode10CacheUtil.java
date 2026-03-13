package com.legacy.ssh.util.cache;

import com.legacy.ssh.service.impl.order.DeepNode11FinalService;

public class DeepNode10CacheUtil {

    private DeepNode11FinalService deepNode11FinalService = new DeepNode11FinalService();

    public String step10(String token) {
        return deepNode11FinalService.step11(token + "-10");
    }
}