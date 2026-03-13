package com.legacy.ssh.interceptor;

import com.legacy.ssh.legacy.integration.DeepNode6Integration;

public class DeepNode5Interceptor {

    private DeepNode6Integration deepNode6Integration = new DeepNode6Integration();

    public String step5(String token) {
        return deepNode6Integration.step6(token + "-5");
    }
}