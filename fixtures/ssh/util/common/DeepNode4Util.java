package com.legacy.ssh.util.common;

import com.legacy.ssh.interceptor.DeepNode5Interceptor;

public class DeepNode4Util {

    private DeepNode5Interceptor deepNode5Interceptor = new DeepNode5Interceptor();

    public String step4(String token) {
        return deepNode5Interceptor.step5(token + "-4");
    }
}