package com.legacy.ssh.action.user;

import com.legacy.ssh.model.user.User;
import com.legacy.ssh.util.cache.LocalCache;
import com.legacy.ssh.util.common.LegacyCodeUtil;

public class UserRegisterAction {

    public String register(User user) {
        if (user == null || user.getUserId() == null) {
            return "FAIL:user invalid";
        }
        LocalCache.put("USER:" + user.getUserId(), user.getDisplayName());
        LegacyCodeUtil.debug("register " + user.getUserId());
        return "OK:registered";
    }
}
