import os
import time
import torch
import torchvision
import torchvision.transforms as transforms
import torch.nn as nn
import torch.optim as optim
from torchvision.models import vgg16
from torch.utils.data import DataLoader, random_split
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score

if __name__ == '__main__':
    print("cuda.is_available " + str(torch.cuda.is_available()))
    
    # Define data transforms
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # Define data directory
    data_dir = "train_data-mc"
    dataset = torchvision.datasets.ImageFolder(root=data_dir, transform=transform)

    # Determine the number of classes in your dataset
    num_classes = len(dataset.classes)

    # Define hyperparameters
    num_epochs = 10
    learning_rate = 0.001
    batch_size = 16

    # Define cross-validation strategy (e.g., 5-fold)
    kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for fold, (train_indices, val_indices) in enumerate(kf.split(range(len(dataset)), dataset.targets)):
        print(f"Fold {fold + 1}:")

        # Split the dataset into training and validation sets for this fold
        train_dataset = torch.utils.data.Subset(dataset, train_indices)
        val_dataset = torch.utils.data.Subset(dataset, val_indices)

        # Create data loaders for training and validation
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4)

        # Define the model
        model = vgg16(pretrained=True)
        model.classifier[6] = nn.Linear(4096, num_classes)

        # Set the device
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        model.to(device)

        # Define the loss function and optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.SGD(model.parameters(), lr=learning_rate, momentum=0.9)

        # Training loop
        for epoch in range(num_epochs):
            epoch_start_time = time.time()
            model.train()
            running_loss = 0.0

            for i, data in enumerate(train_loader, 0):
                inputs, labels = data
                inputs, labels = inputs.to(device), labels.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                running_loss += loss.item()

            # Validation loop
            model.eval()
            y_true = []
            y_pred = []

            with torch.no_grad():
                for data in val_loader:
                    images, labels = data
                    images, labels = images.to(device), labels.to(device)
                    outputs = model(images)
                    _, predicted = torch.max(outputs, 1)

                    y_true.extend(labels.cpu().numpy())
                    y_pred.extend(predicted.cpu().numpy())
            
            accuracy = accuracy_score(y_true, y_pred)
            
            f1_scores = f1_score(y_true, y_pred, average=None)
            epoch_delta_time = time.time() - epoch_start_time

            print(f"F1 Scores (Fold {fold + 1}, Epoch {epoch + 1}, sec {epoch_delta_time}):")
            for class_idx, f1 in enumerate(f1_scores):
                print(f"Class {class_idx}: {f1:.4f}")

            print(f"Accuracy (Fold {fold + 1}, Epoch {epoch + 1}, sec {epoch_delta_time}): {accuracy:.4f}")

        # Save the model for this fold if needed
        torch.save(model.state_dict(), f"modelmc_fold{fold + 1}.pth")