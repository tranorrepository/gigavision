# --------------------------------------------------------
# Result merge modules for PANDA
# Written by Wang Xueyang  (wangxuey19@mails.tsinghua.edu.cn), Version 20200321
# Inspired from DOTA dataset devkit (https://github.com/CAPTAIN-WHU/DOTA_devkit)
# --------------------------------------------------------
from nms import py_cpu_nms,py_cpu_softnms,set_cpu_nms
from d2det.ops.nms.nms_wrapper import soft_nms
import os
import numpy as np
from tqdm import tqdm 
import json
from collections import defaultdict
import random
from demo_visual import merge_result_visual
from concurrent.futures.thread import ThreadPoolExecutor
from ensemble_boxes import nms
import json
import os
try:
    import xml.etree.cElementTree as ET  #解析xml的c语言版的模块
except ImportError:
    import xml.etree.ElementTree as ET


class DetResMerge():
    def __init__(self,
                 resfile,
                 splitannofile,
                 srcannofile,
                 outpath,
                 npyname,
                 test,
                 imgfilters,
                 isload_npy=False,
                 imgext='.jpg',
                 code='utf-8',
                 ext =2 # Pixel extension
                 ):
        """
        :param basepath: base directory for panda image data and annotations
        :param resfile: detection result file path
        :param splitannofile: generated split annotation file
        :param srcannofile: source annotation file
        :param resmode: detection result mode, which can be 'person', 'vehicle', 'headbbox' or 'headpoint'
        :param outpath: output base path for merged result file
        :param outfile: name for merged result file
        :param imgext: ext for the split image format
        """
        self.resfile = resfile
        self.splitannofile = splitannofile
        self.srcannofile = srcannofile
        self.imgfilters=imgfilters
        self.outpath = outpath
        self.imgext = imgext
        self.code = code
        self.respath = resfile
        self.test=test
        self.subimg_width = 1536
        self.subimg_height = 1536
        self.splitannopath = splitannofile
        self.srcannopath = srcannofile
        # self.imagepaths = util.GetFileFromThisRootDir(self.imgpath, ext='jpg')
        if not os.path.exists(self.outpath):
            os.makedirs(self.outpath)
        self.results = defaultdict(list)
        self.npyname=npyname
        self.ext = ext 
        self.isload_npy=isload_npy
        if self.isload_npy:
            print(f"load /root/data/gvision/CrowdDet-master/model/rcnn_emd_refine/outputs/coco_results/{self.npyname}.npy")
            self.results =np.load(f"/root/data/gvision/CrowdDet-master/model/rcnn_emd_refine/outputs/coco_results/{self.npyname}.npy",allow_pickle=True)
        else:
            self.indexResults()
    def keep_dets(self,dets,UP_boundary,temp):
        imgWidth,imgHeight=temp[0],temp[1]
        '''
        :dets: frame_id,left,up,scale,x,y,w,h,score,_  columns=10
        :return dets in small frame [left,up,scale,x,y,w,h,score,_]   columns = 9
        '''
        keep_dets = []
        keep_values=[]
        print(dets[0])
        _,left,up,scale,_,_,_,_,_,_,_ = dets[0]
        right = left + int(self.subimg_width/scale)
        down = up + int(self.subimg_height/scale)
        if up == UP_boundary:
            if left == 0:              # left_up_corner ============
                for det in dets:
                    _,left,up,scale,x,y,w,h,score,number,category_id= det
                    if x+w >= self.subimg_width-self.ext or y+h >= self.subimg_height-self.ext:# if is out of right or down bound
                        continue
                    else:
                        keep_values.append([left,up,scale])
                        keep_dets.append( {'image_id':number, 'bbox': [x,y,w,h], 'score':score, 'category_id': category_id})
            elif right >= imgWidth-1:           # right_up_corner ============
                for det in dets:
                    _,left,up,scale,x,y,w,h,score,number,category_id= det
                    if x <= 0+self.ext or y+h >= self.subimg_height-self.ext:# if is out of left or down bound
                        continue
                    else:
                        keep_values.append([left,up,scale])
                        keep_dets.append( {'image_id':number, 'bbox': [x,y,w,h], 'score':score, 'category_id': category_id})
            else:                      # up_bound ============
                for det in dets:
                    _,left,up,scale,x,y,w,h,score,number,category_id= det
                    if x <= 0+self.ext or y+h >= self.subimg_height-self.ext or x+w >= self.subimg_width-self.ext:# if is out of left or down or right bound
                        continue
                    else:
                        keep_values.append([left,up,scale])
                        keep_dets.append( {'image_id':number, 'bbox': [x,y,w,h], 'score':score, 'category_id': category_id})
        elif left == 0:
            if down >= imgHeight-10:  # left_down_corner ============
                for det in dets:
                    _,left,up,scale,x,y,w,h,score,number,category_id= det
                    if y <= 0+self.ext or x+w >= self.subimg_width-self.ext: # if is out of up or right bound
                        continue
                    else:
                        keep_values.append([left,up,scale])
                        keep_dets.append( {'image_id':number, 'bbox': [x,y,w,h], 'score':score, 'category_id': category_id})
            else:                      # left_bound ============
                for det in dets:
                    _,left,up,scale,x,y,w,h,score,number,category_id= det
                    if y <= 0+self.ext or x+w >= self.subimg_width-self.ext or y+h >= self.subimg_height-self.ext:# if is out of up or right or down bound
                        continue
                    else:
                        keep_values.append([left,up,scale])
                        keep_dets.append( {'image_id':number, 'bbox': [x,y,w,h], 'score':score, 'category_id': category_id})
        elif down >= imgHeight-10: ####################################
            if right >= imgWidth-1: # right_down_corner ============
                for det in dets:
                    _,left,up,scale,x,y,w,h,score,number,category_id= det
                    if x <= 0+self.ext or y <= 0+self.ext:
                        continue
                    else:
                        keep_values.append([left,up,scale])
                        keep_dets.append( {'image_id':number, 'bbox': [x,y,w,h], 'score':score, 'category_id': category_id})
            else:                      # down_bound ============
                for det in dets:
                    _,left,up,scale,x,y,w,h,score,number,category_id= det
                    if x <= 0+self.ext or y <= 0+self.ext or x+w >= self.subimg_width-self.ext:
                        continue
                    else:
                        keep_values.append([left,up,scale])
                        keep_dets.append( {'image_id':number, 'bbox': [x,y,w,h], 'score':score, 'category_id': category_id})
        elif right >= imgWidth-1:   # right_broud ============
            for det in dets:
                _,left,up,scale,x,y,w,h,score,number,category_id= det
                if x <= 0+self.ext or y <= 0+self.ext or y+h >= self.subimg_height-self.ext:
                    continue
                else:
                    keep_values.append([left,up,scale])
                    keep_dets.append( {'image_id':number, 'bbox': [x,y,w,h], 'score':score, 'category_id': category_id})
        else:                          # inner_part ============
            for det in dets:
                _,left,up,scale,x,y,w,h,score,number,category_id= det
                if x <= 0+self.ext or y <= 0+self.ext or x+w >= self.subimg_width-self.ext or y+h >= self.subimg_height-self.ext: ##################################
                    continue
                else:
                    keep_values.append([left,up,scale])
                    keep_dets.append( {'image_id':number, 'bbox': [x,y,w,h], 'score':score, 'category_id': category_id})

        if len(keep_dets)>0:
            return keep_dets,keep_values
        else:
            return None

    def indexResults(self):
        print('Loading result json file: {}'.format(self.respath))
        with open(self.respath, 'r') as load_f:
            reslist = json.load(load_f)
        print("bboxex_num",len(reslist))#498
        print('Loading split annotation json file: {}'.format(self.splitannopath))
        with open(self.splitannopath, 'r') as load_f:
            splitanno = json.load(load_f)
        indexedresults = defaultdict(list)
        if self.test:
            tempannos={}
            imgfilters=self.imgfilters
            # imgfilters=["15_24"]
            for imgfilter in imgfilters:
                tempannos.update({i:j for i,j in splitanno.items() if imgfilter in i })
            splitanno=tempannos
        def say(iss):
            filename, annodict=iss[0],iss[1]
            imageid = annodict['image id']
            # print("imageid",imageid)
            for resdict in reslist:
                resimageid = resdict['image_id']
                if resimageid == imageid:
                    # print("1111",resdict) {'image_id': 253, 'category_id': 1, 'bbox': [981.3349609375, 322.8221435546875, 22.030517578125, 32.01666259765625], 'score': 0.16039377450942993}
                    # print("2222",resimageid)
                    # print("1111",type(resdict))
                    # print("2222",type(resimageid))
                    indexedresults[filename].append(resdict)

            return indexedresults
        # print("splitanno",splitanno)
        executor = ThreadPoolExecutor(max_workers=1)
        func_var = [[file_name,dict_value] for file_name,dict_value in splitanno.items()]
        pbar = tqdm(total=len(splitanno), ncols=50)
        for temp in executor.map(say,func_var):
            # print(temp)
            indexedresults.update(temp)
            pbar.update(1)
        pbar.close()
        self.results = indexedresults
        np.save(f"/root/data/gvision/CrowdDet-master/model/rcnn_emd_refine/outputs/coco_results/{self.npyname}.npy",indexedresults )
        print("save ***index.npy*** as :",f"/root/data/gvision/CrowdDet-master/model/rcnn_emd_refine/outputs/coco_results/{self.npyname}.npy")

    def mergeResults(self,outfile,merge_input_mode="xywh",is_nms=True,nms_thresh=0.9,nms_name="nms"):
        """
        :param is_nms: do non-maximum suppression on after merge
        :param nms_thresh: non-maximum suppression IoU threshold
        :return:
        """
        print('Loading source annotation json file: {}'.format(self.srcannopath))
        with open(self.srcannopath, 'r') as load_f:
            srcanno = json.load(load_f)
        mergedresults = defaultdict(list)
        # random.seed(0)
        # print("len",len(self.results))
        keep_input=[]
        for (filename, objlist) in self.results.items():
        # for (filename, objlist) in random.sample(self.results.items(),2):
            srcfile, scale, left, up  = filename.split('___')
            srcfile =srcfile.replace('_IMG', '/IMG')+".jpg"
            up =up[:-4]
            # print(filename, objlist)
            # srcimageid =srcfile[-2:]
            # print(srcfile)
            srcimageid = srcanno[srcfile]['image id']
            print("srcimageid",srcimageid)
            # print(srcfile, scale, left, up )

            # srcfile, paras = filename.split('___')#srcfile, paras 15_Nanshani_Park_IMG_15_04 0.5__4224__6144.jpg
            # # print("srcfile, paras",srcfile, paras )
            # srcfile = srcfile.replace('_IMG', '/IMG') + self.imgext#02_Xili_Crossroad_IMG_02_01___0.5__0__0.jpg
            # srcimageid = srcanno[srcfile]['image id']
            # scale, left, up = paras.replace(self.imgext, '').split('__')#scale, left, up  0.5 4224 6144
            # # print(srcfile, scale, left, up )
            # print(f"before objlist {len(objlist)}")
            if not keep_fliter:
                for objdict in objlist:
                    mergedresults[srcimageid].append([*recttransfer(objdict['bbox'], float(scale), int(left), int(up),merge_input_mode),objdict['score'], objdict['category_id'],objdict['image_id']])
            if keep_fliter:
                keep_input=keep_input+[[srcimageid,int(left), int(up),float(scale),i['bbox'][0],i['bbox'][1],i['bbox'][2],i['bbox'][3],i['score'],i['image_id'],i['category_id']] for i in objlist]
            # keep_input.append([[srcimageid,int(left), int(up),float(scale),i['bbox'][0],i['bbox'][1],i['bbox'][2],i['bbox'][3],i['score'],i['image_id'],i['category_id']] for i in objlist])
        if keep_fliter:
            print(f"before keep {len(keep_input)}")
            if 391<=srcimageid<=420:#14otcUP_boundary
                keep_dets,_keep_values=self.keep_dets(np.array(keep_input),UP_boundary[0],PANDA_TEST_SIZE[0])
            if 421<=srcimageid<=450:#15 nanshangongyuan
                keep_dets,_keep_values=self.keep_dets(np.array(keep_input),UP_boundary[1],PANDA_TEST_SIZE[1])
            if 451<=srcimageid<=465:#16xiaoxue----------01
                keep_dets,_keep_values=self.keep_dets(np.array(keep_input),UP_boundary[2],PANDA_TEST_SIZE[2])
            if 466<=srcimageid<=480:#16xiaoxue--------02
                keep_dets,_keep_values=self.keep_dets(np.array(keep_input),UP_boundary[3],PANDA_TEST_SIZE[2])
            if 481<=srcimageid<=510:#17zhongguan
                keep_dets,_keep_values=self.keep_dets(np.array(keep_input),UP_boundary[4],PANDA_TEST_SIZE[3])
            if 511<=srcimageid<=540:#18xilin-------01
                keep_dets,_keep_values=self.keep_dets(np.array(keep_input),UP_boundary[5],PANDA_TEST_SIZE[4])
            if 541<=srcimageid<=555:#18xilin----------02
                keep_dets,_keep_values=self.keep_dets(np.array(keep_input),UP_boundary[6],PANDA_TEST_SIZE[5])
            print(f"after keep {len(keep_dets)}")
            for objdict,keep_value in zip(keep_dets,_keep_values):
                left, up,scale=keep_value[0],keep_value[1],keep_value[2]
                # print("objdict",objdict)#{'image_id': 7110, 'bbox': [47.7, 866.2, 198.8, 442.8], 'score': 0.83231, 'category_id': 1}
                mergedresults[srcimageid].append([*recttransfer(objdict['bbox'], float(scale), int(left), int(up),merge_input_mode),
                        objdict['score'], objdict['category_id'],objdict['image_id']])
                
        img_size = {}
        for anno in srcanno:
            # print(srcanno[anno]['image id'])
            img_size[srcanno[anno]['image id']] = srcanno[anno]['image size']
        if is_nms:
            if nms_name=="nms":
                for (imageid, objlist) in mergedresults.items():
                    keep = py_cpu_nms(np.array(objlist), nms_thresh)
                    outdets = []
                    for index in keep:
                        outdets.append(objlist[index])
                    mergedresults[imageid] = outdets
            if nms_name=="setnms":
                for (imageid, objlist) in mergedresults.items():
                    print("input nms element",objlist[0])#[829, 5939, 923, 6000, 0.24672751128673553, 1, 149]
                    print(f"before setnms {nms_thresh} ",len(objlist))
                    # print(imageid)
                    keep=np.array(objlist)[set_cpu_nms(np.array(objlist), nms_thresh)].tolist()
                    # print("keep",keep,"\n",len(keep),type(keep))
                    print(f"{imageid} after setnms_{nms_thresh} ",len(keep))
                    mergedresults[imageid] = keep
            if nms_name=="emnms":
                for (imageid, objlist) in mergedresults.items():
                    size_anno = img_size[imageid]
                    boxes = [[obj[0] / size_anno['width'], obj[1] / size_anno['height'],
                              obj[2] / size_anno['width'], obj[3] / size_anno['height']] for obj in objlist]
                    scores = [obj[4] for obj in objlist]
                    labels = [obj[5] for obj in objlist]
                    boxes, scores, labels = nms([boxes], [scores], [labels])
                    boxes[:, [0, 2]] *= size_anno['width']
                    boxes[:, [1, 3]] *= size_anno['height']
                    outdets = [x[0] + [x[1], x[2]] for x in zip(boxes.tolist(), scores.tolist(), labels.tolist())]
                    mergedresults[imageid] = outdets
            if nms_name=="softnms":
                for (imageid, objlist) in mergedresults.items():
                    print(f"{imageid} before softnms_{nms_thresh} ",len(objlist))
                    newdets,keep=soft_nms(np.array(objlist),iou_thr=nms_thresh, method='gaussian',sigma=0.5, min_score=1e-3)#'gaussian''linear',
                    # keep =py_cpu_softnms(np.array(objlist),thresh=nms_thresh, Nt=0.02, sigma=0.5, method=1)
                    # print(keep)
                    outdets = []
                    for index in keep:
                        outdets.append(objlist[index])
                    print(f"{imageid} after softnms_{nms_thresh} ",len(keep))
                    mergedresults[imageid] = outdets
        savelist = []
        def say2(iss):
            imageid, objlist=iss[0],iss[1]
            # print(imageid, objlist)
            templist=[]
            for obj in objlist:#obj [22528, 1270, 24576, 1, 1.0, 4]
                # print(obj)
                templist.append({
                    "image_id": imageid,
                    "category_id": obj[5],
                    "bbox": tlbr2tlwh(obj[:4]),
                    "score": obj[4]
                })
            if test:
                print(f"fliter berfore len {len(templist)}")
            if 391<=imageid<=420:#14otc
                templist=fliter(templist,fliterscore["14_OCT"],AnotPath="/root/data/gvision/dataset/xml/14_OCT_Habour.xml",
                segma_woh=3,segma_area=3,up_bound=4000,down_bound=None,down_fs=0.95)
            if 421<=imageid<=450:#15 nanshangongyuan
                templist=fliter(templist,fliterscore["15_nanshan"],AnotPath="/root/data/gvision/dataset/xml/15_Nanshani_Park.xml",
                segma_woh=3,segma_area=3,up_bound=1500,down_bound=7000,down_fs=None)
            if 451<=imageid<=465:#16xiaoxue----------01
                templist=fliter(templist,fliterscore["1601_shool"],AnotPath="/root/data/gvision/dataset/xml/IMG_16_01_head.xml",
                segma_woh=3,segma_area=3,up_bound=0,down_bound=None,down_fs=None)
            if 466<=imageid<=480:#16xiaoxue--------02
                templist=fliter(templist,fliterscore["1602_shool"],AnotPath="/root/data/gvision/dataset/xml/IMG_16_25_02_.xml",
                segma_woh=3,segma_area=3,up_bound=0,down_bound=None,down_fs=None)
            if 481<=imageid<=510:#17zhongguan
                templist=fliter(templist,fliterscore["17_newzhongguan"],AnotPath="/root/data/gvision/dataset/xml/17_New_Zhongguan.xml",
                segma_woh=3,segma_area=3,up_bound=6000,down_bound=7000,down_fs=0.5)
            if 511<=imageid<=540:#18xilin-------01
                templist=fliter(templist,fliterscore["1801_xilin"],AnotPath="/root/data/gvision/dataset/xml/IMG_18_01_01.xml",
                segma_woh=3,segma_area=3,up_bound=4000,down_bound=None,down_fs=None)
            if 541<=imageid<=555:#18xilin----------02
                templist=fliter(templist,fliterscore["1802_xilin"],AnotPath="/root/data/gvision/dataset/xml/IMG_18_02.xml",
                segma_woh=3,segma_area=3,up_bound=4000,down_bound=None,down_fs=None)
            # templist=del_inter(templist)
            # print(f"del_inter after len {len(templist)}")
            if test:
                print(f"fliter after len {len(templist)}")
            return templist
        executor = ThreadPoolExecutor(max_workers=80)
        func_var = [[file_name,dict_value] for file_name,dict_value in mergedresults.items()]

        print("merge bbox into self'image start ")
        pbar2= tqdm(total=len(mergedresults), ncols=50)
        for temp in executor.map(say2,func_var):
            savelist+=temp
            pbar2.update(1)
        pbar2.close()
        with open(os.path.join(self.outpath, outfile), 'w', encoding=self.code) as f:
            dict_str = json.dumps(savelist, indent=2)
            f.write(dict_str)
        print(f"save ***results*** json :{os.path.join(self.outpath, outfile)}")
def fliter(rectange_list,fliterscore,AnotPath,segma_woh,segma_area,up_bound,down_bound,down_fs):
    dis_woh=[i['bbox'][3]/(i['bbox'][2]+0.00001)  for i in rectange_list]
    dis_area=[i['bbox'][3]*i['bbox'][2]  for i in rectange_list]
    u_woh=np.mean(dis_woh)
    std_woh=np.std(dis_woh)*segma_woh
    u_area=np.mean(dis_area)
    std_area=np.std(dis_area)*segma_area
    rectange_list=[i for i in rectange_list if (u_woh-std_woh<i['bbox'][3]/(i['bbox'][2]+0.00001)<u_woh+std_woh and i['score'] >fliterscore and u_area-std_area<i['bbox'][3]/(i['bbox'][2]+0.00001)<u_area+std_area and i['bbox'][1]>up_bound)]
    if test:
        print("fliter  outlier after ",len(rectange_list))
    rectange_list=GetAnnotBoxLoc(AnotPath,rectange_list)
    if down_bound and down_fs:
        rectange_list=[i for i in rectange_list if (i['bbox'][1]>down_bound and i['score']>down_fs) or i['bbox'][1]<down_bound]
    if test:
        print("fliter downfs after",len(rectange_list))
    return rectange_list
def del_inter(rectange_list):#AnotPath VOC标注文件路径
    backlist=[]
    # print(f"forbid zone before {len(rectange_list)}")
    # pbar3= tqdm(total=len(rectange_list), ncols=50)
    for a in rectange_list:
        i=a["bbox"]
        left,up,right,down=int(i[0]),int(i[1]),int(i[0]+i[2]),int(i[3]+i[1])
        templist=[]
        inter_xml=np.zeros(len(rectange_list),dtype=float)
        for id,k in enumerate(rectange_list):
            j=k["bbox"]
            xmin,ymin,xmax,ymax=int(j[0]),int(j[1]),int(j[0]+j[2]),int(j[3]+j[1])
            if xmax <= left or right <= xmin or ymax <= up or down <= ymin:
                intersection = 0
            else:
                lens = min(xmax, right) - max(xmin, left)
                wide = min(ymax, down) - max(ymin, up)
                intersection = lens * wide
                # print("*"*6,intersection)
                # print(i[2]*i[3])
            inter_xml[id]=intersection/(i[2]*i[3]+0.00001)
        # print(np.where(inter_xml<0.99)[0].shape[0])
        if np.where(inter_xml<0.8)[0].shape[0]==len(rectange_list)-1:
            backlist.append(a)
    #     pbar3.update(1)
    # pbar3.close()
        # else:
        #     print(np.where(inter_xml==0)[0].shape[0]==len(ObjectSet))
        #     print("del")
    # print(f"forbid zone after {len(backlist)}")
    # return backlist+templist
    return backlist
def GetAnnotBoxLoc(AnotPath,rectange_list):#AnotPath VOC标注文件路径
    tree = ET.ElementTree(file=AnotPath)  #打开文件，解析成一棵树型结构
    root = tree.getroot()#获取树型结构的根
    ObjectSet=root.findall('object')#找到文件中所有含有object关键字的地方，这些地方含有标注目标
    backlist=[]
    # print(f"forbid zone before {len(rectange_list)}")

    for a in rectange_list:
        i=a["bbox"]
        left,up,right,down=i[0],i[1],i[0]+i[2],i[3]+i[1]
        templist=[]
        inter_xml=np.zeros(len(ObjectSet),dtype=float)
        for k,Object in enumerate(ObjectSet):
            BndBox=Object.find('bndbox')
            xmin= int(BndBox.find('xmin').text)#-1 #-1是因为程序是按0作为起始位置的
            ymin= int(BndBox.find('ymin').text)#-1
            xmax= int(BndBox.find('xmax').text)#-1
            ymax= int(BndBox.find('ymax').text)#-1
            templist.append({
                    "image_id": 481,
                    "category_id": 1,
                    "bbox": [xmin,ymin,xmax-xmin,ymax-ymin],
                    "score":1
                })

            if xmax <= left or right <= xmin or ymax <= up or down <= ymin:
                intersection = 0
            else:
                lens = min(xmax, right) - max(xmin, left)
                wide = min(ymax, down) - max(ymin, up)
                intersection = lens * wide
                # print("*"*60,intersection)
                # print(i[2]*i[3])
            inter_xml[k]=intersection/(i[2]*i[3])
        if np.where(inter_xml<0.05)[0].shape[0]==len(ObjectSet):#则没有与bbox相交的xmlforbidzone < param or ==0
            backlist.append(a)
        # else:
        #     print(np.where(inter_xml==0)[0].shape[0]==len(ObjectSet))
        #     print("del")
    # print(f"forbid zone after {len(backlist)}")
    # return backlist+templist
    return backlist

def recttransfer(rect, scale, left, up,merge_input_mode):
    if merge_input_mode=="xyxy":
        xmin, ymin, xmax, ymax = rect
    if merge_input_mode=="xywh":
        xmin, ymin, w, h = rect
        xmax, ymax = xmin + w, ymin + h
    

    # return [int(temp / scale) for temp in [xmin + left, ymin + up, xmax + left, ymax + up]]
    return [int(temp) for temp in [xmin/scale + left, ymin/scale + up, xmax/scale + left, ymax/scale  + up]]


def tlbr2tlwh(rect):
    xmin, ymin, xmax, ymax = rect
    w, h = xmax - xmin, ymax - ymin
    return [xmin, ymin, w, h]
def full():
    """
    global variable
    """
    global PANDA_TEST_SIZE,fliterscore,UP_boundary,keep_fliter,test
    PANDA_TEST_SIZE=[
    [26573,15052], # 9
    [32609,24457], # 10
    [31760,23810],
    [26583,14957],
    [26583,14957],
    [26573,15052]]
    UP_boundary=[4500,1417,0,0,5357,4205,52]
    #是否use keep_dets()
    keep_fliter=1
    fliterscore={"14_OCT":0.1,"15_nanshan":0.5,"1601_shool":0.2,"1602_shool":0.3,"17_newzhongguan":0.4,"1801_xilin":0.4,"1802_xilin":0.4}
    network="crowdet"
    weights=""
    cls_="full"#head 
    test=1
    resfile="/root/data/gvision/CrowdDet-master/model/rcnn_emd_refinet/visiblebody/outputs/eval_dump/allvboxdump_3nms0.35prethre0.4.json"
    # resfile="/root/data/gvision/CrowdDet-master/model/rcnn_emd_refinet/outputs/eval_dump/testalldunms0.35prethre0.4.json"
    outpath=f"/root/data/gvision/my_merge/{cls_}/coco_results"
    imgfilters=["14_02","16_02" ,"16_14","16_16","15_24","17_02" ,"18_40","18_01","17_01"]
    imgfilters=["15_24"]
    outfile=f"inter{network}{weights}_{cls_}.json"#save image prefix
    savepath=f"/root/data/gvision/my_merge/{cls_}/visual/{network}"
    #softnms nms setnms emnms
    nms_name="softnms"
    nms_thresh=0.7
    merge=DetResMerge(resfile=resfile,outpath=outpath,
                            # splitannofile="/root/data/rubzz/ruby/ruby_output/test/person/split_test_method2_person.json",
                            splitannofile="/root/data/gvision/dataset/predict/person/test_person.json",
                            srcannofile="/root/data/gvision/dataset/raw_data/image_annos/person_bbox_test.json",
                            # srcannofile="/root/data/gvision/dataset/predict/17_01/image_annos/1701.json",
                            npyname=outfile[:-4]+f"{nms_name}",
                            test=test,
                            imgfilters=imgfilters,
                            isload_npy=False,
                            )
    merge.mergeResults(outfile=outfile,is_nms=True,nms_thresh=nms_thresh,nms_name=nms_name)
    # merge.mergeResults(merge_input_mode="xywh",is_nms=True,nms_thresh=0.9)
    merge_result_visual(image_folder_test="/root/data/gvision/dataset/raw_data/image_test",
                result_path=os.path.join(outpath,outfile),
                annos_path="/root/data/gvision/dataset/raw_data/image_annos/person_bbox_test.json",
                savepath=savepath,
                output_prefix=outfile[:-4]+f"{nms_name}{nms_thresh}",
                imgfilters=imgfilters,
                test=test,
                mode="xywh",
                num=10)#mode: input_bbox mode
def main():
    full()
if __name__ == "__main__":
    main()