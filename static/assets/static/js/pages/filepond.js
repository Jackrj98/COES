
FilePond.registerPlugin(
  FilePondPluginImagePreview
)

// Filepond: Basic
FilePond.create(document.querySelector(".basic-filepond"), {
  credits: null,
  allowImagePreview: false,
  allowMultiple: false,
  allowFileEncode: false,
  required: false,
  storeAsFile: true,
})

// Filepond: Image Preview
FilePond.create(document.querySelector(".image-preview-filepond"), {
  credits: null,
  allowImagePreview: true,
  allowImageFilter: false,
  allowImageExifOrientation: false,
  allowImageCrop: false,
  acceptedFileTypes: ["image/png", "image/jpg", "image/jpeg"],
  fileValidateTypeDetectType: (source, type) =>
    new Promise((resolve, reject) => {
      // Do custom type detection here and return with promise
      resolve(type)
    }),
  storeAsFile: true,
})
