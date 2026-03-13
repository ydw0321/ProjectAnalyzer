package com.legacy.ssh.interceptor;

import com.legacy.ssh.util.cache.LocalCache;

public class AuthorizationInterceptor {

    public boolean check(String token) {
        if (token == null || token.trim().isEmpty()) {
            return false;
        }
        String user = LocalCache.get("TOKEN:" + token);
        return user != null;
    }
}
