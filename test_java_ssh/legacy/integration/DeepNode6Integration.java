package com.legacy.ssh.legacy.integration;

import com.legacy.ssh.job.DeepNode7Job;

public class DeepNode6Integration {

    private DeepNode7Job deepNode7Job = new DeepNode7Job();

    public String step6(String token) {
        return deepNode7Job.step7(token + "-6");
    }
}