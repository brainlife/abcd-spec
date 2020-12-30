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
                
                
