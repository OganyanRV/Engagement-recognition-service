def calc_iou(first_bbox, second_bbox):

    first_bbox = first_bbox[[1,0, 3, 2]]
    second_bbox = second_bbox[[1,0, 3, 2]]
    
    inter_x_start = max(first_bbox[0], second_bbox[0])
    inter_y_start = max(first_bbox[1], second_bbox[1])
    inter_x_end = min(first_bbox[0] + first_bbox[2], second_bbox[0] + second_bbox[2])
    inter_y_end = min(first_bbox[1] + first_bbox[3], second_bbox[1] + second_bbox[3])

    area_inter = abs(max((inter_x_end - inter_x_start, 0)) * max((inter_y_end - inter_y_start), 0))
    
    if area_inter == 0:
        return 0.0

    area_first = abs(first_bbox[2] * first_bbox[3])
    area_second = abs(second_bbox[2] * second_bbox[3])
    
    return area_inter / (area_first + area_second - area_inter)


def nms(detections_list, iou_thr=0.5):
    detections = sorted(detections_list[0], key=lambda x: x[-2], reverse=True)

    suppressed_idx = []

    for idx, fi_box in enumerate(detections):
        if idx in suppressed_idx:
            continue

        for jdx in range(idx + 1, len(detections)):
            if jdx in suppressed_idx:
                continue

            se_box = detections[jdx]
            iou = calc_iou(fi_box[:-2], se_box[:-2])

            if iou > iou_thr:
                suppressed_idx.append(jdx)

    new_detections = []
    for idx, detection in enumerate(detections):
        if(idx not in suppressed_idx):
            new_detections.append(detection.unsqueeze(0))
            
    return new_detections