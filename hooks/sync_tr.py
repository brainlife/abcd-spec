from bids import BIDSLayout
import nibabel


#######################################################
# The following is the original solution proposed here:
# https://neurostars.org/t/bids-validator-error-tr-mismatch-between-nifti-header-and-json-file-and-bids-validator-is-somehow-finding-tr-0-best-solution/1799/19

def set_tr(img, tr):
    header = img.header.copy()
    zooms = header.get_zooms()[:3] + (tr,)
    header.set_zooms(zooms)
    return img.__class__(img.get_data().copy(), img.affine, header)

def sync_tr(bids_root):
    layout = BIDSLayout(bids_root)
    for nii in layout.get(extensions=['.nii', '.nii.gz']):
        metadata = layout.get_metadata(nii.path)
        if 'RepetitionTime' in metadata:
            img = nb.load(nii.path)
            if img.header.get_zooms()[3:] != (metadata['RepetitionTime'],):
                fixed_img = set_tr(img, metadata['RepetitionTime'])
                fixed_img.to_filename(nii.path)
                
                
##############################################################
# The following is our adapted solution proposed for brainlife    

def set_tr(img, tr):
    header = img.header.copy()
    #zooms = header.get_zooms()[:3] + (tr,)
    header['pixdim'][4] = tr
    print(f"Overwriting TR in the header with TR={tr}")
    return img.__class__(img.get_data().copy(), img.affine, header)

def sync_tr(bids_root):
    layout = BIDSLayout(bids_root)
    for nii in layout.get(extension=['.nii.gz']):
        metadata = layout.get_metadata(nii.path)
        if 'RepetitionTime' in metadata:
            img = nib.load(nii.path)
            #if img.header.get_zooms()[3:] != (metadata['RepetitionTime'],):
            if img.header['pixdim'][4] != (metadata['RepetitionTime'],):
                print("Mismatch between the TR value in the json file and in the header.")
                print(f"Json file has TR={metadata['RepetitionTime']}")
                print(f"Header has TR={img.header['pixdim'][4]}")
                fixed_img = set_tr(img, metadata['RepetitionTime'])
                fixed_img.to_filename(nii.path)
                
                
