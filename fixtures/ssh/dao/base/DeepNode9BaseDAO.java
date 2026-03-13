package com.legacy.ssh.dao.base;

import com.legacy.ssh.util.cache.DeepNode10CacheUtil;

public class DeepNode9BaseDAO {

    private DeepNode10CacheUtil deepNode10CacheUtil = new DeepNode10CacheUtil();

    public String step9(String token) {
        return deepNode10CacheUtil.step10(token + "-9");
    }
}