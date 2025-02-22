import torch
import numpy as np
from utils.metric import cal_psnr, cal_mse

def closure_ei(net, dataloader, physics, transform,
                    optimizer, criterion_mc, criterion_ei,
                    alpha, dtype, device, reportpsnr=False):
    # run本函数 == 一轮epoch
    loss_mc_seq, loss_ei_seq, loss_seq, psnr_seq, mse_seq = [], [], [], [], []
    for i, x in enumerate(dataloader):
        x = x[0] if isinstance(x, list) else x
        if len(x.shape)==3:
            x = x.unsqueeze(1)  # [bs, 1, h, w]
        x = x.type(dtype).to(device) # ground-truth signal x, 维度为m

        y0 = physics.A(x.type(dtype).to(device)) # generate measurement input y, 维度为n
        x0 = physics.A_dagger(y0) # range input (A^+y), 通过approximatte inverse把y变成维度m(假如A是已知的，那这一步等于Measurement Consistency，例如inpainting和k-space sample，否则这一步结果比MC差)

        x1 = net(x0)  # 重建结果
        y1 = physics.A(x1)  # 对inpainting和k-space sample来说，这里y1应该肯定等于y0

        # equivariant imaging（开始加入transform）: x2, x3
        x2 = transform.apply(x1)
        x3 = net(physics.A_dagger(physics.A(x2)))

        loss_mc = criterion_mc(y1, y0)
        loss_ei = criterion_ei(x3, x2)

        loss = loss_mc + alpha['ei'] * loss_ei

        loss_mc_seq.append(loss_mc.item())
        loss_ei_seq.append(loss_ei.item())
        loss_seq.append(loss.item())

        if reportpsnr:
            psnr_seq.append(cal_psnr(x1, x))
            mse_seq.append(cal_mse(x1, x))

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    loss_closure = [np.mean(loss_mc_seq), np.mean(loss_ei_seq), np.mean(loss_seq)]

    if reportpsnr:
        loss_closure.append(np.mean(psnr_seq))
        loss_closure.append(np.mean(mse_seq))

    return loss_closure
