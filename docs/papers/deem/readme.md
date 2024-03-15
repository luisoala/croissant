```python
import mlcroissant as mlc
     
# 1. Create Croissant datasets
croissant_ds = mlc.Dataset(jsonld="croissant.json")

# 2. Load Croissant datasets
croissant_url = "https://datasets-server.huggingface.co/croissant?dataset=fashion_mnist"

# 3. Use Croissant dataset in your ML workload
builder = tfds.core.dataset_builders.CroissantBuilder(
    jsonld=croissant_file,
    record_set_names=["record_set_fashion_mnist"],
    file_format='array_record',
    data_dir=data_dir,
)

train, test = builder.as_data_source(split=['default[:80%]', 'default[80%:]'])
```
