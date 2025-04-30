from datetime import datetime
import os
import torch
import gc
import logging
import warnings
import glob
from diffusers import StableDiffusionPipeline
from diffusers.utils.logging import disable_default_handler
from diffusers.schedulers import (
    DDIMScheduler,
    EulerDiscreteScheduler,
    EulerAncestralDiscreteScheduler,
    DPMSolverMultistepScheduler,
    DPMSolverSinglestepScheduler,
    HeunDiscreteScheduler,
    LMSDiscreteScheduler,
    PNDMScheduler,
    UniPCMultistepScheduler,
    KDPM2DiscreteScheduler,
    KDPM2AncestralDiscreteScheduler,
    DEISMultistepScheduler,
)
from contextlib import redirect_stdout, redirect_stderr
import io
import re
import time


# Thiết lập logging
# os.makedirs(
#     os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..","logs"),
#     exist_ok=True,
# )

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)

log_filename = f"image_generation_{datetime.now().strftime('%Y-%m-%d')}.log"
log_filepath = os.path.join(log_dir, log_filename)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler(),
    ],
)

# Từ điển ánh xạ scheduler
SCHEDULER_MAP = {
    "euler": EulerDiscreteScheduler,
    "euler_a": EulerAncestralDiscreteScheduler,
    "ddim": DDIMScheduler,
    "dpm": DPMSolverMultistepScheduler,
    "dpm_single": DPMSolverSinglestepScheduler,
    "heun": HeunDiscreteScheduler,
    "lms": LMSDiscreteScheduler,
    "pndm": PNDMScheduler,
    "unipc": UniPCMultistepScheduler,
    "kdpm2": KDPM2DiscreteScheduler,
    "kdpm2_a": KDPM2AncestralDiscreteScheduler,
    "deis": DEISMultistepScheduler,
    "dpm++_2m_karras": DPMSolverMultistepScheduler,
    "dpm++_sde_karras": DPMSolverSinglestepScheduler,
}

KARRAS_COMPATIBLE_SCHEDULERS = [
    "euler",
    "euler_a",
    "dpm",
    "dpm_single",
    "heun",
    "lms",
    "unipc",
    "deis",
    "dpm++_2m_karras",
    "dpm++_sde_karras",
]

# Tắt cảnh báo và logging không cần thiết
warnings.filterwarnings("ignore", category=UserWarning, module="diffusers")
disable_default_handler()
os.environ["DIFFUSERS_NO_ADVISORY_WARNINGS"] = "1"
logging.getLogger("diffusers").setLevel(logging.ERROR)

# Tính toán thư mục gốc của dự án
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..",".."))

model_dir = os.path.join(project_root, "models", "model")
embedding_dir = os.path.join(project_root, "models", "embedding")
lora_dir = os.path.join(project_root, "models", "lora")

# Hàm quét thư mục với tối ưu hóa
def scan_directory(directory):
    configs = []
    if not os.path.exists(directory):
        logging.error(f"Thư mục {directory} không tồn tại")
        return configs
    for file_path in glob.glob(os.path.join(directory, "*.safetensors")) + glob.glob(os.path.join(directory, "*.pt")):
        if os.path.getsize(file_path) > 0:  # Kiểm tra file không rỗng
            token = os.path.splitext(os.path.basename(file_path))[0]
            configs.append({"path": file_path, "token": token})
    if not configs:
        logging.warning(f"Không tìm thấy file .safetensors hoặc .pt trong {directory}")
    return configs

embedding_configs = scan_directory(embedding_dir)
lora_configs = scan_directory(lora_dir)

model_path = os.path.join(project_root, "models", "model", "trunGPT.safetensors")

if not os.path.exists(model_path):
    logging.error(f"Không tìm thấy tệp mô hình tại: {model_path}")
    raise FileNotFoundError("Không tìm thấy tệp mô hình .safetensors trong thư mục model")

# Hàm mã hóa prompt embeddings
def encode_prompt_embeddings(pipe, prompt, negative_prompt, chunk_size=77):
    try:
        if not hasattr(pipe, 'text_encoder') or pipe.text_encoder is None:
            logging.error("Text encoder không tồn tại trong pipeline")
            return None, None

        tokenized_output = pipe.tokenizer(
            prompt, return_tensors="pt", truncation=False, padding=False
        )
        tokenized_prompt = tokenized_output.input_ids.to("cuda")
        prompt_length = tokenized_prompt.shape[-1]

        concat_embeds = []
        for i in range(0, prompt_length, chunk_size):
            chunk = tokenized_prompt[:, i:i+chunk_size]
            if chunk.shape[-1] < chunk_size:
                padding = torch.zeros(
                    (chunk.shape[0], chunk_size - chunk.shape[-1]),
                    dtype=chunk.dtype,
                    device=chunk.device,
                )
                chunk = torch.cat([chunk, padding], dim=-1)
            embeds = pipe.text_encoder(chunk)[0]
            concat_embeds.append(embeds)
        prompt_embeds = torch.cat(concat_embeds, dim=1)

        tokenized_neg_output = pipe.tokenizer(
            negative_prompt,
            return_tensors="pt",
            truncation=False,
            padding="max_length",
            max_length=max(prompt_length, 77),
        )
        tokenized_negative = tokenized_neg_output.input_ids.to("cuda")
        concat_neg_embeds = []
        for i in range(0, tokenized_negative.shape[-1], chunk_size):
            chunk = tokenized_negative[:, i:i+chunk_size]
            if chunk.shape[-1] < chunk_size:
                padding = torch.zeros(
                    (chunk.shape[0], chunk_size - chunk.shape[-1]),
                    dtype=chunk.dtype,
                    device=chunk.device,
                )
                chunk = torch.cat([chunk, padding], dim=-1)
            embeds = pipe.text_encoder(chunk)[0]
            concat_neg_embeds.append(embeds)
        negative_prompt_embeds = torch.cat(concat_neg_embeds, dim=1)

        return prompt_embeds, negative_prompt_embeds
    except Exception as e:
        logging.error(f"Lỗi khi mã hóa prompt embeddings: {str(e)}")
        return None, None

# Hàm tải embedding
def load_embeddings(pipe, prompt, negative_prompt, embedding_configs):
    loaded_embeddings = []
    failed_embeddings = []
    tokens = set(re.findall(r'\b\w+\b', f"{prompt} {negative_prompt}".lower()))

    for emb_config in embedding_configs:
        emb_token = emb_config["token"]
        if emb_token in tokens:
            emb_path = emb_config["path"]
            try:
                if os.path.getsize(emb_path) > 0:
                    pipe.load_textual_inversion(
                        emb_path, token=emb_token, mean_resizing=True
                    )
                    loaded_embeddings.append(emb_token)
                else:
                    logging.warning(f"File embedding {emb_path} rỗng, bỏ qua")
                    failed_embeddings.append(emb_token)
            except Exception as e:
                logging.error(f"Lỗi khi tải embedding {emb_token} từ {emb_path}: {str(e)}")
                failed_embeddings.append(emb_token)

    if loaded_embeddings:
        logging.info(f"Đã tải embedding: {', '.join(loaded_embeddings)}")
    if failed_embeddings:
        logging.warning(f"Không thể tải embedding: {', '.join(failed_embeddings)}")
    return loaded_embeddings

# Hàm tải LoRA
def load_loras(pipe, prompt, final_prompt, lora_configs, default_lora_scale):
    loaded_loras = []
    failed_loras = []
    active_lora_ids = []
    active_lora_scales = []

    # Phân tích các thẻ LoRA trong prompt
    import re
    lora_matches = re.findall(r'\<lora:([^:]+):(\d*\.\d+)\>', f"{prompt} {final_prompt}")
    lora_dict = {token: float(scale) for token, scale in lora_matches}

    for i, lora_config in enumerate(lora_configs):
        lora_token = lora_config["token"]
        lora_path = lora_config["path"]
        lora_id = f"lora_{i}"

        if lora_token in lora_dict:
            try:
                if os.path.getsize(lora_path) > 0:
                    # Tải LoRA mà không xóa adapter cũ
                    pipe.load_lora_weights(lora_path, adapter_name=lora_id)
                    active_lora_ids.append(lora_id)
                    active_lora_scales.append(lora_dict[lora_token])
                    loaded_loras.append(f"{lora_token} (scale: {lora_dict[lora_token]})")
                else:
                    logging.warning(f"File LoRA {lora_path} rỗng, bỏ qua")
                    failed_loras.append(lora_token)
            except Exception as e:
                logging.error(f"Lỗi khi tải LoRA {lora_token} từ {lora_path}: {str(e)}")
                failed_loras.append(lora_token)

    # Thiết lập các adapter đã tải
    if active_lora_ids:
        pipe.set_adapters(active_lora_ids, adapter_weights=active_lora_scales)
        logging.info(f"Đã thiết lập adapters: {active_lora_ids} với trọng số {active_lora_scales}")

    # Ghi log kết quả
    if loaded_loras:
        logging.info(f"Đã tải LoRA: {', '.join(loaded_loras)}")
    if failed_loras:
        logging.warning(f"Không thể tải LoRA: {', '.join(failed_loras)}")

    return active_lora_ids, active_lora_scales

def genImage(
    prompt,
    negative_prompt="",
    steps=40,
    batch_size=1,
    height=512,
    width=512,
    seed=None,
    guidance_scale=7.5,
    clip_skip=2,
    scheduler_type="euler",
    default_lora_scale=0.8,
    denoising_strength=0.3,
    hires_fix=True,
    hires_scale=1.5,
):
    """
    Tạo ảnh từ prompt sử dụng Stable Diffusion Pipeline.

    Args:
        prompt (str): Mô tả ảnh cần tạo.
        negative_prompt (str): Mô tả những gì không muốn xuất hiện trong ảnh.
        steps (int): Số bước suy luận.
        batch_size (int): Số ảnh tạo ra mỗi lần.
        height (int): Chiều cao ảnh.
        width (int): Chiều rộng ảnh.
        seed (int, optional): Seed cho generator.
        guidance_scale (float): Mức độ ảnh hưởng của prompt.
        clip_skip (int): Số lớp CLIP bỏ qua.
        scheduler_type (str): Loại scheduler sử dụng.
        default_lora_scale (float): Scale mặc định cho LoRA.
        denoising_strength (float, optional): Mức độ denoising, từ 0.0 đến 1.0.
        hires_fix (bool): Kích hoạt tinh chỉnh độ phân giải cao.
        hires_scale (float): Tỷ lệ phóng đại cho hires fix.

    Returns:
        str or list: Đường dẫn đến ảnh đã lưu hoặc danh sách đường dẫn.
    """
    start_time = time.time()

    # Kiểm tra tham số đầu vào
    if not isinstance(prompt, str) or not prompt.strip():
        logging.error("Prompt không hợp lệ")
        raise ValueError("Prompt phải là chuỗi không rỗng")
    if steps < 1:
        logging.error("Số bước phải lớn hơn 0")
        raise ValueError("Số bước phải lớn hơn 0")
    if batch_size < 1:
        logging.error("Batch size phải lớn hơn 0")
        raise ValueError("Batch size phải lớn hơn 0")
    if height % 8 != 0 or width % 8 != 0:
        logging.error("Chiều cao và chiều rộng phải chia hết cho 8")
        raise ValueError("Chiều cao và chiều rộng phải chia hết cho 8")
    if guidance_scale < 0:
        logging.error("Guidance scale phải không âm")
        raise ValueError("Guidance scale phải không âm")
    if denoising_strength is not None and not (0.0 <= denoising_strength <= 1.0):
        logging.error("denoising_strength phải nằm trong khoảng [0.0, 1.0]")
        raise ValueError("denoising_strength phải nằm trong khoảng [0.0, 1.0]")

    # Ghi log cho denoising_strength
    if denoising_strength is not None:
        logging.info(f"Sử dụng denoising_strength: {denoising_strength}")

    # Kiểm tra bộ nhớ GPU

    free_memory = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()
    if free_memory < 2 * 1024 * 1024 * 1024:
        logging.warning("Bộ nhớ GPU thấp, có thể gây lỗi CUDA out of memory")
        hires_fix = False
        gc.collect()
        torch.cuda.empty_cache()


    # Kiểm tra sự tồn tại của tệp mô hình
    if not os.path.exists(model_path):
        logging.error(f"Tệp mô hình không tồn tại tại: {model_path}")
        raise FileNotFoundError(f"Tệp mô hình không tồn tại tại: {model_path}")

    pipe = None
    try:
        # Khởi tạo pipeline
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            pipe = StableDiffusionPipeline.from_single_file(
                model_path,
                torch_dtype=torch.float16,
                use_safetensors=True,
                safety_checker=None,
                mean_resizing=True,
            ).to("cuda")
            logging.info(f"Khởi tạo pipeline thành công trong {time.time() - start_time:.2f}s")

        # Thiết lập scheduler
        scheduler_class = SCHEDULER_MAP.get(
            scheduler_type.lower(), DPMSolverMultistepScheduler
        )
        try:
            scheduler_kwargs = {}
            if scheduler_type.lower() in KARRAS_COMPATIBLE_SCHEDULERS:
                scheduler_kwargs["use_karras_sigmas"] = True
            if scheduler_type.lower() == "dpm++_sde_karras":
                scheduler_kwargs["algorithm_type"] = "sde-dpmsolver++"
            pipe.scheduler = scheduler_class.from_config(
                pipe.scheduler.config, **scheduler_kwargs
            )
            logging.info(
                f"Đã thiết lập scheduler: {scheduler_type}"
                + (" với Karras sampling" if scheduler_kwargs.get("use_karras_sigmas") else "")
            )
        except Exception as e:
            logging.error(f"Không thể khởi tạo scheduler {scheduler_type}: {e}")
            pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                pipe.scheduler.config, use_karras_sigmas=True
            )

        # Xây dựng negative_prompt
        base_negative_prompt = "ng_deepnegative_v1_75t,badhandv4,(bad thighs),(bad legs),(bad anatomy:1.5),(low quality),blurry,(extra fingers),(missing fingers),(fused fingers)"
        if negative_prompt:
            negative_prompt = f"{negative_prompt}, {base_negative_prompt}"
        else:
            negative_prompt = base_negative_prompt

        # Load embedding
        load_embeddings(pipe, prompt, negative_prompt, embedding_configs)

        # Xử lý prompt và LoRA
        keywords = [
            "best quality", "masterpiece", "highly detailed", "ultra highres",
            "photorealistic", "ultra-detailed", "high-resolution", "cinematic lighting"
        ]
        cleaned_prompt = prompt.lower()
        for keyword in keywords:
            cleaned_prompt = cleaned_prompt.replace(keyword.lower(), "").strip()

        if "girl" in cleaned_prompt.lower() or "woman" in cleaned_prompt.lower():
            final_prompt = f"best quality,masterpiece,highly detailed,ultra highres,photorealistic,ultra-detailed,high-resolution,cinematic lighting,highly detailed face,beautiful face,<lora:Detail:1.0>,<lora:tifa_face:1.0>,{cleaned_prompt}"
        else:
            final_prompt = f"best quality,masterpiece,highly detailed,ultra highres,photorealistic,ultra-detailed,high-resolution,cinematic lighting,{cleaned_prompt}"

        # Load LoRA
        active_lora_ids, active_lora_scales = load_loras(
            pipe, prompt, final_prompt, lora_configs, default_lora_scale
        )

        # Bật xFormers
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            logging.warning("Không thể bật xFormers, tiếp tục mà không tối ưu hóa")

        # Thiết lập seed
        generator = None
        if seed is not None:
            generator = torch.Generator(device="cuda").manual_seed(seed)
            logging.info(f"Đã thiết lập generator với seed: {seed}")

        # Xử lý prompt embeddings
        prompt_embeds, negative_prompt_embeds = encode_prompt_embeddings(
            pipe, final_prompt, negative_prompt
        )



        if free_memory < 2 * 1024 * 1024 * 1024:
            logging.warning("Bộ nhớ GPU thấp, có thể gây lỗi CUDA out of memory")
            hires_fix = False
            gc.collect()
            torch.cuda.empty_cache()

        # Tạo ảnh
        logging.info(f"Bắt đầu tạo ảnh với prompt: {prompt}")
        create_time = time.time()
        try:
            pipeline_kwargs = {
                "prompt": final_prompt if prompt_embeds is None else None,
                "prompt_embeds": prompt_embeds,
                "negative_prompt": negative_prompt if negative_prompt_embeds is None else None,
                "negative_prompt_embeds": negative_prompt_embeds,
                "num_inference_steps": steps,
                "num_images_per_prompt": batch_size,
                "height": height,
                "width": width,
                "guidance_scale": guidance_scale,
                "clip_skip": clip_skip,
                "cross_attention_kwargs": {"scale": 1.0},
                "eta": 0.0,
                "guidance_rescale": 0.0,  # Tắt guidance rescale để giữ chi tiết
                "generator": generator,
                "use_progress_bar": False,
            }
            if denoising_strength is not None:
                pipeline_kwargs["strength"] = denoising_strength

            images = pipe(**pipeline_kwargs).images

            # Áp dụng hires fix nếu được bật
            if hires_fix:
                gc.collect()
                torch.cuda.empty_cache()
                for i, img in enumerate(images):
                    hires_kwargs = {
                        "image": img,
                        "prompt": final_prompt if prompt_embeds is None else None,
                        "prompt_embeds": prompt_embeds,
                        "negative_prompt": negative_prompt if negative_prompt_embeds is None else None,
                        "negative_prompt_embeds": negative_prompt_embeds,
                        "num_inference_steps": int(steps * 0.5),
                        "guidance_scale": guidance_scale,
                        "strength": 0.3,
                        "target_size": (int(width * hires_scale), int(height * hires_scale)),
                    }
                    images[i] = pipe(**hires_kwargs).images[0]

        except Exception as e:
            logging.error(f"Lỗi khi tạo ảnh: {str(e)}")
            raise RuntimeError("Không thể tạo ảnh")

        # Lưu ảnh
        output_dir = os.path.join(project_root, "models", "img")
        os.makedirs(output_dir, exist_ok=True)
        output_paths = []
        save_time = time.time()
        for i, img in enumerate(images):
            output_path = os.path.join(output_dir, f"image_{i}_{int(time.time())}.png")
            try:
                img.save(output_path, format="PNG", quality=100)  # Tăng chất lượng lưu
                output_paths.append(output_path)
                logging.info(f"Đã lưu ảnh tại: {output_path}")
            except Exception as e:
                logging.error(f"Lỗi khi lưu ảnh {output_path}: {str(e)}")
                continue

        if not output_paths:
            logging.error("Không thể lưu bất kỳ ảnh nào")
            raise RuntimeError("Không thể lưu bất kỳ ảnh nào")

        logging.info(f"Hoàn thành tạo ảnh trong {time.time() - start_time:.2f}s")
        return output_paths[0] if len(output_paths) == 1 else output_paths

    finally:
        if pipe is not None:
            del pipe
        gc.collect()
        torch.cuda.empty_cache()
