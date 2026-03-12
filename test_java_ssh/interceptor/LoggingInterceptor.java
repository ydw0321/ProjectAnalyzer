package com.legacy.ssh.interceptor;

import com.legacy.ssh.util.common.LegacyCodeUtil;

public class LoggingInterceptor {

    public void before(String uri) {
        LegacyCodeUtil.debug("before:" + uri);
    }

    public void after(String uri, long start) {
        long cost = System.currentTimeMillis() - start;
        LegacyCodeUtil.debug("after:" + uri + ",cost=" + cost);
    }
}
